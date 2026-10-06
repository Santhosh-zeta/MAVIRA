"""Analyst review. Reviews are appended; generated results are never modified.
The *effective* result is the generated result with the latest OVERRIDE applied."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import AnalystReview, Assessment
from app.services import audit

OVERRIDABLE = {
    "criticality_tier": {"LOW", "MEDIUM", "HIGH", "CRITICAL"},
    "ai_usage": {"YES", "NO", "INCONCLUSIVE"},
    "risk_class": {"NONE_IDENTIFIED", "LOW", "MEDIUM", "HIGH", "CRITICAL"},
}
TEXT_OVERRIDES = {"risk_rationale", "recommended_action", "ai_usage_summary"}


class ReviewError(ValueError):
    pass


def snapshot(a: Assessment) -> dict:
    return {"criticality_tier": a.criticality_tier, "criticality_score": a.criticality_score,
            "ai_usage": a.ai_usage, "ai_confidence": a.ai_confidence, "risk_class": a.risk_class,
            "risk_score": a.risk_score, "provider_status": a.provider_status,
            "risk_rationale": a.risk_rationale, "ai_usage_summary": a.ai_usage_summary}


def effective(a: Assessment) -> dict:
    eff = snapshot(a)
    eff["review_status"] = a.review_status
    overrides = [r for r in a.reviews if r.decision == "OVERRIDE"]
    if overrides:
        last = overrides[-1]
        eff.update(last.overrides or {})
        eff["override_reason"], eff["override_by"] = last.reason, last.analyst
    approvals = [r for r in a.reviews if r.decision in ("APPROVE", "OVERRIDE")]
    if approvals:
        eff["reviewed_by"], eff["reviewed_at"] = approvals[-1].analyst, approvals[-1].created_at.isoformat()
    return eff


def submit(db: Session, a: Assessment, *, decision: str, analyst: str, reason: str | None,
           overrides: dict | None) -> AnalystReview:
    decision = decision.upper()
    if decision not in ("APPROVE", "OVERRIDE", "REQUEST_REASSESSMENT"):
        raise ReviewError("decision must be APPROVE, OVERRIDE or REQUEST_REASSESSMENT")
    if a.status not in ("COMPLETED", "PARTIAL"):
        raise ReviewError("only completed assessments can be reviewed")
    analyst = (analyst or "").strip()
    if not analyst:
        raise ReviewError("analyst name is required")
    clean: dict = {}
    if decision == "OVERRIDE":
        if not reason or len(reason.strip()) < 10:
            raise ReviewError("an override requires a reason of at least 10 characters")
        for k, v in (overrides or {}).items():
            if k in OVERRIDABLE:
                if v not in OVERRIDABLE[k]:
                    raise ReviewError(f"invalid value for {k}: {v}")
                clean[k] = v
            elif k in TEXT_OVERRIDES and isinstance(v, str) and v.strip():
                clean[k] = v.strip()[:4000]
        if not clean:
            raise ReviewError("an override must change at least one field")
    if decision == "REQUEST_REASSESSMENT" and (not reason or len(reason.strip()) < 5):
        raise ReviewError("a reassessment request requires a reason")
    review = AnalystReview(assessment_id=a.id, decision=decision, analyst=analyst[:120],
                           reason=(reason or "").strip()[:4000] or None, overrides=clean or None,
                           original_snapshot=snapshot(a))
    db.add(review)
    a.review_status = {"APPROVE": "APPROVED", "OVERRIDE": "OVERRIDDEN",
                       "REQUEST_REASSESSMENT": "REASSESSMENT_REQUESTED"}[decision]
    audit.record(db, f"REVIEW_{decision}", actor=analyst, run_id=a.run_id, assessment_id=a.id,
                 overrides=clean, reason=reason)
    db.flush()
    a.reviews.append(review) if review not in a.reviews else None
    return review
