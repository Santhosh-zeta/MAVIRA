"""Single source of truth for turning ORM rows into API / export payloads."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AISignal, Assessment, AssessmentRun, AssessmentSource, Evidence, SearchRun, Source, Vendor
from app.services.review.service import effective

NATURE_WEIGHT_ZERO = {"INDUSTRY_COMMENTARY"}


def iso(d):
    return d.isoformat() if d else None


def source_dict(s: Source, include_content: bool = False) -> dict:
    d = {"id": s.id, "url": s.url, "domain": s.domain, "title": s.title, "source_type": s.source_type,
         "reliability_level": s.reliability_level, "reliability_score": s.reliability_score,
         "published_date": iso(s.published_date), "retrieved_at": iso(s.retrieved_at),
         "content_hash": s.content_hash, "collection_method": s.collection_method, "cache_origin": s.cache_origin,
         "status": s.status, "http_status": s.http_status, "etag": s.etag, "last_modified": s.last_modified,
         "error": s.error}
    if include_content:
        d["content"] = s.content
        d["chunks"] = [{"idx": c.idx, "char_start": c.char_start, "ai_relevant": c.ai_relevant, "length": len(c.text)}
                       for c in s.chunks]
    return d


def evidence_dict(e: Evidence, vendor: Vendor | None = None) -> dict:
    s = e.source
    return {"id": e.id, "assessment_id": e.assessment_id,
            "vendor_ref": vendor.vendor_ref if vendor else None, "vendor_name": vendor.name if vendor else None,
            "claim": e.claim, "exact_excerpt": e.exact_excerpt, "excerpt_start": e.excerpt_start,
            "excerpt_end": e.excerpt_end, "validation_status": e.validation_status,
            "rejection_reason": e.rejection_reason, "nature": e.nature, "ai_types": e.ai_types or [],
            "interpretation": e.interpretation, "directness": e.directness, "service_relevance": e.service_relevance,
            "strength_score": e.strength_score, "strength_level": e.strength_level,
            "strength_breakdown": e.strength_breakdown, "confidence": e.confidence, "proposed_by": e.proposed_by,
            "source": source_dict(s) if s else None}


def vendor_dict(v: Vendor) -> dict:
    return {"id": v.id, "vendor_ref": v.vendor_ref, "name": v.name, "description": v.description,
            "service": v.service, "category": v.category, "website": v.website,
            "business_process": v.business_process, "operational_dependency": v.operational_dependency,
            "data_classification": v.data_classification, "data_volume": v.data_volume,
            "row_number": v.row_number, "is_example": v.is_example, "import_id": v.import_id}


def assessment_summary(a: Assessment) -> dict:
    eff = effective(a) if a.status in ("COMPLETED", "PARTIAL") else {}
    return {"id": a.id, "run_id": a.run_id, "vendor_id": a.vendor_id, "status": a.status, "stage": a.stage,
            "criticality_tier": a.criticality_tier, "criticality_score": a.criticality_score,
            "depth_tier": a.depth_tier, "ai_usage": a.ai_usage, "ai_confidence": a.ai_confidence,
            "ai_types": a.ai_types or [], "risk_class": a.risk_class, "risk_score": a.risk_score,
            "evidence_strength_level": a.evidence_strength_level, "top_evidence_strength": a.top_evidence_strength,
            "provider_status": a.provider_status, "review_status": a.review_status,
            "human_review_required": a.human_review_required, "completed_at": iso(a.completed_at),
            "effective": eff, "errors": a.errors or []}


def assessment_detail(db: Session, a: Assessment) -> dict:
    run = db.get(AssessmentRun, a.run_id)
    vendor = db.get(Vendor, a.vendor_id)
    evid = list(db.scalars(select(Evidence).where(Evidence.assessment_id == a.id)))
    links = list(db.scalars(select(AssessmentSource).where(AssessmentSource.assessment_id == a.id)))
    searches = list(db.scalars(select(SearchRun).where(SearchRun.assessment_id == a.id).order_by(SearchRun.executed_at)))
    signals = list(db.scalars(select(AISignal).where(AISignal.assessment_id == a.id)))
    d = assessment_summary(a)
    d.update({
        "vendor": vendor_dict(vendor),
        "run": {"id": run.id, "osint_mode": run.osint_mode, "search_provider": run.search_provider,
                "analyzer": run.analyzer, "model_name": run.model_name, "prompt_version": run.prompt_version,
                "methodology_version": run.methodology_version, "methodology_version_id": run.methodology_version_id,
                "created_at": iso(run.created_at), "completed_at": iso(run.completed_at)},
        "criticality_factors": a.criticality_factors, "criticality_rationale": a.criticality_rationale,
        "depth_plan": a.depth_plan, "ai_usage_summary": a.ai_usage_summary, "ai_usage_basis": a.ai_usage_basis,
        "negative_evidence": a.negative_evidence, "risk_rationale": a.risk_rationale, "risk_inputs": a.risk_inputs,
        "stage_log": a.stage_log or [],
        "evidence": [evidence_dict(e, vendor) for e in sorted(
            evid, key=lambda e: (e.validation_status != "VALID", e.nature in NATURE_WEIGHT_ZERO,
                                 -(e.strength_score or 0)))],
        "signals": [{"evidence_id": s.evidence_id, "nature": s.nature, "ai_type": s.ai_type, "exposure": s.exposure}
                    for s in signals],
        "providers": [{"provider_name": p.provider_name, "provider_type": p.provider_type, "confidence": p.confidence,
                       "service_linkage": p.service_linkage, "evidence_id": p.evidence_id,
                       "evidence_excerpt": p.evidence_excerpt} for p in a.providers],
        "risk_factors": [{"category": r.category, "score": r.score, "weight": r.weight,
                          "contribution": r.contribution, "status": r.status, "rationale": r.rationale}
                         for r in a.risk_factors],
        "recommendations": [{"rule_id": r.rule_id, "priority": r.priority, "category": r.category,
                             "action": r.action, "due_in_days": r.due_in_days, "grounded_on": r.grounded_on}
                            for r in sorted(a.recommendations, key=lambda r: r.priority)],
        "reviews": [{"id": r.id, "decision": r.decision, "analyst": r.analyst, "reason": r.reason,
                     "overrides": r.overrides, "original_snapshot": r.original_snapshot,
                     "reassessment_run_id": r.reassessment_run_id, "created_at": iso(r.created_at)}
                    for r in a.reviews],
        "sources": [{**source_dict(l.source), "category": l.category, "from_cache": l.from_cache,
                     "ai_relevant_chunks": l.ai_relevant_chunks} for l in links],
        "searches": [{"category": s.category, "query": s.query, "provider": s.provider, "status": s.status,
                      "result_count": s.result_count, "latency_ms": s.latency_ms, "error": s.error}
                     for s in searches],
    })
    return d


def latest_assessments(db: Session, import_id: str | None = None) -> list[Assessment]:
    """Latest completed-or-in-progress assessment per vendor (by run creation time)."""
    q = (select(Assessment, AssessmentRun, Vendor.vendor_ref)
         .join(AssessmentRun, AssessmentRun.id == Assessment.run_id)
         .join(Vendor, Vendor.id == Assessment.vendor_id))
    if import_id:
        q = q.where(AssessmentRun.import_id == import_id)
    q = q.order_by(AssessmentRun.created_at.desc())
    seen, out = set(), []
    for a, _, ref in db.execute(q):
        if ref in seen:
            continue
        seen.add(ref)
        out.append(a)
    return out


def current_import_id(db: Session) -> str | None:
    from app.models import WorkbookImport
    return db.scalar(select(WorkbookImport.id).order_by(WorkbookImport.uploaded_at.desc()))
