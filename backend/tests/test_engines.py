"""Unit tests: criticality, depth, methodology, strength, usage, risk, recommendations."""
from __future__ import annotations

from datetime import date

import pytest
import yaml

from app.services.ai.usage import EvidenceView, determine
from app.services.criticality.engine import calculate, parse_largest_quantity
from app.services.depth.engine import plan
from app.services.evidence import strength
from app.services.methodology.loader import Methodology, MethodologyError, parse_yaml
from app.services.recommendations.engine import RecContext, generate
from app.services.risk.engine import RiskInputs, calculate as risk_calc


# ------------------------------------------------------------------ criticality
EXPECTED_TIERS = {"V-001": "HIGH", "V-002": "CRITICAL", "V-003": "HIGH", "V-004": "MEDIUM",
                  "V-005": "CRITICAL", "V-006": "CRITICAL"}


@pytest.mark.parametrize("ref,tier", EXPECTED_TIERS.items())
def test_criticality_tiers_for_meridian_vendors(ref, tier, vendor_rows, methodology):
    r = calculate(vendor_rows[ref], methodology)
    assert r.tier == tier
    assert set(r.factors) == {"operational_dependency", "data_sensitivity", "payment_flow", "regulatory_exposure", "data_volume"}
    assert abs(sum(f.contribution for f in r.factors.values()) - r.score) < 1e-3
    assert r.methodology_version.startswith(methodology["version"])
    assert "Weighted score" in r.rationale and r.tier.title() in r.rationale


def test_criticality_is_deterministic(vendor_rows, methodology):
    a = calculate(vendor_rows["V-002"], methodology)
    b = calculate(vendor_rows["V-002"], methodology)
    assert (a.score, a.tier) == (b.score, b.tier)


def test_privileged_access_escalation_is_explained(vendor_rows, methodology):
    r = calculate(vendor_rows["V-001"], methodology)
    assert r.weighted_tier == "MEDIUM" and r.tier == "HIGH"
    assert r.escalations[0]["rule"] == "privileged_production_access"
    assert "Escalated Medium -> High" in r.rationale


def test_unrecognised_dependency_uses_default_and_says_so(vendor_rows, methodology):
    row = vendor_rows["V-004"] | {"operational_dependency": "Sometimes"}
    r = calculate(row, methodology)
    assert r.factors["operational_dependency"].score == methodology["criticality"]["operational_dependency_map"]["default"]
    assert "analyst to confirm" in r.factors["operational_dependency"].basis


def test_volume_parsing():
    assert parse_largest_quantity("240 million transactions") == 240_000_000
    assert parse_largest_quantity("for 38,000 wealth clients") == 38_000
    assert parse_largest_quantity("2.1 million messages") == 2_100_000
    assert parse_largest_quantity("Not applicable") == 0


def test_weights_come_from_configuration(vendor_rows, methodology):
    cfg = yaml.safe_load(yaml.safe_dump(methodology.config))
    cfg["criticality"]["weights"] = {"operational_dependency": 1.0, "data_sensitivity": 0.0, "payment_flow": 0.0,
                                     "regulatory_exposure": 0.0, "data_volume": 0.0}
    m2 = Methodology(None, "test", "x" * 64, cfg)
    r = calculate(vendor_rows["V-003"], m2)
    assert r.score == pytest.approx(0.5)


def test_methodology_validation_rejects_bad_weights(methodology):
    cfg = yaml.safe_load(yaml.safe_dump(methodology.config))
    cfg["risk"]["weights"]["DATA_EXPOSURE"] = 0.9
    with pytest.raises(MethodologyError):
        parse_yaml(yaml.safe_dump(cfg))


# ------------------------------------------------------------------ depth
def test_depth_tiers_are_nested_and_criticality_driven(vendor_rows, methodology):
    plans = {t: plan(t, vendor_rows["V-002"], methodology) for t in ("LOW", "MEDIUM", "HIGH", "CRITICAL")}
    order = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    for lo, hi in zip(order, order[1:]):
        assert set(plans[lo].source_categories) < set(plans[hi].source_categories)
        assert plans[lo].max_sources < plans[hi].max_sources
    assert plans["CRITICAL"].human_review_required and plans["CRITICAL"].negative_evidence_review
    assert not plans["LOW"].provider_investigation
    assert any("site:fiserv.com" in q.query for q in plans["LOW"].queries)
    assert "Full review" in plans["CRITICAL"].description()


# ------------------------------------------------------------------ strength
def test_recency_bands(methodology):
    cfg = methodology["evidence_strength"]
    today = date(2026, 10, 6)
    assert strength.recency(date(2026, 1, 8), today, cfg) == 1.0
    assert strength.recency(date(2017, 3, 20), today, cfg) == 0.2
    assert strength.recency(None, today, cfg) == cfg["recency_unknown"]


def test_strength_score_and_breakdown(methodology):
    inp = strength.StrengthInputs(reliability_score=1.0, directness="vendor_self_statement",
                                  excerpt="BNY has AI-based anomaly detection in its own Payment Validation solution",
                                  ai_types=["Fraud Detection", "Machine Learning"], provider_count=0,
                                  service_relevance=0.6, corroborated=False, published=None, as_of=date.today())
    score, level, br = strength.score(inp, methodology)
    assert 0 <= score <= 100 and level in ("VERY_STRONG", "STRONG", "MODERATE", "WEAK")
    assert abs(sum(v["points"] for v in br.values()) - score) < 0.5
    weak = strength.score(strength.StrengthInputs(0.25, "commentary", "AI will change things", ["Unknown"], 0, 0, False,
                                                  date(2015, 1, 1), date.today()), methodology)
    assert weak[1] == "WEAK" and weak[0] < score


# ------------------------------------------------------------------ usage
def _ev(nature, s, src="s1", dom="vendor.com", lvl="DIRECT", neg=False, specific=False):
    return EvidenceView(id=src + nature, source_id=src, domain=dom, nature=nature, ai_types=["Generative AI"],
                        strength=s, level="STRONG" if s >= 65 else "MODERATE", reliability_level=lvl, excerpt="x",
                        negative=neg, service_specific=specific)


def test_yes_requires_confirming_evidence(methodology):
    assert determine([_ev("PRODUCT_FEATURE", 70)], methodology, searches=3, sources_checked=2, vendor_short="V").usage == "YES"
    two = [_ev("PRODUCT_FEATURE", 50, "a"), _ev("SERVICE_INTEGRATED", 50, "b", "other.com")]
    assert determine(two, methodology, searches=3, sources_checked=2, vendor_short="V").usage == "YES"
    assert determine([_ev("MARKETING_ONLY", 95)], methodology, searches=3, sources_checked=2,
                     vendor_short="V").usage == "INCONCLUSIVE"
    assert determine([_ev("PRODUCT_FEATURE", 50)], methodology, searches=3, sources_checked=2,
                     vendor_short="V").usage == "INCONCLUSIVE"


def test_absence_of_evidence_is_never_no(methodology):
    r = determine([], methodology, searches=9, sources_checked=3, vendor_short="V")
    assert r.usage == "INCONCLUSIVE"
    assert "NO MEANINGFUL PUBLIC EVIDENCE IDENTIFIED WITHIN ASSESSED OSINT SCOPE" in r.basis
    assert "not a finding that the vendor does not use AI" in r.basis


def test_no_requires_direct_negative_statement(methodology):
    r = determine([_ev("UNKNOWN", 70, neg=True)], methodology, searches=3, sources_checked=2, vendor_short="V")
    assert r.usage == "NO"


def test_confidence_separate_from_strength(methodology):
    r = determine([_ev("PRODUCT_FEATURE", 70)], methodology, searches=3, sources_checked=2, vendor_short="V")
    assert 0 < r.confidence <= 0.97 and r.top_strength == 70


# ------------------------------------------------------------------ risk
def _risk(**kw):
    base = dict(criticality_tier="CRITICAL", data_sensitivity=1.0, operational_dependency=1.0, regulatory_exposure=1.0,
                ai_usage="YES", ai_exposure=0.6, ai_types=["Fraud Detection"], natures=["PRODUCT_FEATURE"],
                provider_status="not_disclosed", providers=[])
    base.update(kw)
    return RiskInputs(**base)


def test_no_ai_signal_means_none_identified(methodology):
    r = risk_calc(_risk(ai_usage="INCONCLUSIVE", ai_exposure=0.0, ai_types=[], natures=[]), methodology)
    assert r.classification == "NONE_IDENTIFIED" and r.score == 0
    assert "not a confirmed absence" in r.rationale


def test_ai_use_alone_does_not_mean_high_risk(methodology):
    r = risk_calc(_risk(criticality_tier="LOW", data_sensitivity=0.2, operational_dependency=0.25,
                        regulatory_exposure=0.3, ai_exposure=0.2, ai_types=["Generative AI"],
                        provider_status="service_linked"), methodology)
    assert r.classification in ("LOW", "MEDIUM")


def test_unknowns_are_labelled_not_assumed(methodology):
    r = risk_calc(_risk(), methodology)
    statuses = {c.category: c.status for c in r.categories}
    assert statuses["DATA_RETENTION_RISK"].startswith("UNKNOWN / NOT PUBLICLY DISCLOSED")
    assert statuses["MODEL_PROVIDER_TRANSPARENCY"].startswith("UNKNOWN")
    assert len(r.categories) == 9


def test_risk_monotonic_in_data_sensitivity(methodology):
    lo = risk_calc(_risk(data_sensitivity=0.2), methodology).score
    hi = risk_calc(_risk(data_sensitivity=1.0), methodology).score
    assert hi > lo


def test_service_unconfirmed_discount_and_floor(methodology):
    confirmed = risk_calc(_risk(service_confirmed=True), methodology)
    vendor_level = risk_calc(_risk(service_confirmed=False), methodology)
    assert vendor_level.ai_presence < confirmed.ai_presence
    low = risk_calc(_risk(service_confirmed=False, data_sensitivity=0.1, operational_dependency=0.1,
                          regulatory_exposure=0.1, ai_exposure=0.25, ai_types=["NLP"]), methodology)
    assert low.classification == "HIGH" and low.floors          # floor for Critical vendor + confirmed AI


# ------------------------------------------------------------------ recommendations
def test_recommendations_are_grounded(methodology):
    c = RecContext(criticality="CRITICAL", ai_usage="YES", ai_signal_present=True, ai_presence=0.9,
                   provider_status="not_disclosed", providers=[], data_sensitivity=1.0, decision_impact=0.9,
                   decision_types=["Fraud Detection"], natures=["PRODUCT_FEATURE"],
                   evidence_texts={"e1": "the integration of third-party artificial intelligence models with our services"},
                   service_short="DNA core banking platform")
    recs = generate(c, methodology)
    ids = [r.rule_id for r in recs]
    assert {"provider_disclosure", "data_to_external_models", "human_oversight",
            "vendor_disclosed_third_party_model_risk", "escalate_unconfirmed", "monitor"} <= set(ids)
    assert recs[0].priority == "P1"
    third = next(r for r in recs if r.rule_id == "vendor_disclosed_third_party_model_risk")
    assert third.grounded_on["evidence_ids"] == ["e1"]
    assert "every 3 months" in next(r for r in recs if r.rule_id == "monitor").action


def test_inconclusive_critical_gets_questionnaire_not_ai_free(methodology):
    c = RecContext(criticality="CRITICAL", ai_usage="INCONCLUSIVE", ai_signal_present=False, ai_presence=0.0,
                   provider_status="not_disclosed", providers=[], data_sensitivity=0.6, decision_impact=0.0,
                   decision_types=[], natures=[], evidence_texts={}, service_short="RTP")
    ids = [r.rule_id for r in generate(c, methodology)]
    assert "questionnaire_inconclusive_high_tier" in ids and "provider_disclosure" not in ids
