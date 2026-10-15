"""HTTP routes. Handlers validate input and delegate to services."""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import actor, client_key, require_api_key, require_role, upload_limiter
from app.core.config import get_settings
from app.db.session import get_db
from app.models import (
    Assessment, AssessmentRun, AuditEvent, Evidence, MethodologyVersion, Source, Vendor, WorkbookImport,
)
from app.services import audit
from app.services.export.excel_writer import export_workbook
from app.services.export.serializers import (
    assessment_detail, assessment_summary, current_import_id, evidence_dict, iso, latest_assessments, source_dict,
    vendor_dict,
)
from app.services.ingestion.excel_parser import WorkbookError
from app.services.methodology.loader import MethodologyError, active_methodology, methodology_by_id, register
from app.services.pipeline.orchestrator import STAGES, describe_analyzer
from app.services.review.service import ReviewError, submit
from app.services.runs import create_import, start_run
from app.core.security import validate_xlsx_upload
from app.workers.queue import dispatch

router = APIRouter(prefix="/api", dependencies=[Depends(require_api_key)])


# ---------------------------------------------------------------- system
@router.post("/reset")
def reset_all_data(db: Session = Depends(get_db)):
    """Wipe all assessment data so a fresh import can be uploaded."""
    for model in [Evidence, Source, Assessment, AssessmentRun, AuditEvent, WorkbookImport, Vendor, MethodologyVersion]:
        db.query(model).delete()
    db.commit()
    return {"status": "cleared"}


@router.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(select(1))
    s = get_settings()
    analyzer, model, _ = describe_analyzer()
    return {"status": "ok", "osint_mode": s.osint_mode.upper(), "search_provider": s.search_provider,
            "analyzer": analyzer, "llm_enabled": model is not None, "worker_mode": s.worker_mode,
            "data_egress": _egress_statement(s, model)}


def _egress_statement(s, model) -> list[str]:
    out = []
    if s.osint_mode.upper() == "LIVE":
        out.append(f"Search queries (vendor name, domain, service keywords) are sent to {s.search_provider}.")
        out.append("Public vendor web pages are fetched directly from the vendor's or third parties' servers.")
    else:
        out.append("No network egress for OSINT: the cached snapshot shipped with the platform is used.")
    if model:
        out.append(f"Public page text and vendor name/category/service are sent to the LLM {model}. No Meridian customer data.")
    else:
        out.append("No LLM in use: evidence is extracted by the deterministic rule-based analyzer locally.")
    return out


# ---------------------------------------------------------------- imports
@router.post("/imports")
async def upload(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db),
                 who: str = Depends(actor)):
    if not upload_limiter.allow(client_key(request)):
        raise HTTPException(429, "Too many uploads; try again in a minute")
    s = get_settings()
    data = await file.read(s.max_upload_mb * 1024 * 1024 + 1)
    try:
        validate_xlsx_upload(file.filename or "", data, s.max_upload_mb)
        imp, result = create_import(db, file.filename or "upload.xlsx", data, actor=who)
    except (ValueError, WorkbookError) as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"import_id": imp.id if imp else None, "accepted": imp is not None, "validation": result.report()}


@router.get("/imports")
def list_imports(db: Session = Depends(get_db)):
    rows = db.scalars(select(WorkbookImport).order_by(WorkbookImport.uploaded_at.desc())).all()
    return [{"id": i.id, "filename": i.filename, "uploaded_at": iso(i.uploaded_at), "vendor_count": i.vendor_count,
             "sha256": i.file_sha256, "status": i.status} for i in rows]


@router.get("/imports/{import_id}")
def get_import(import_id: str, db: Session = Depends(get_db)):
    imp = db.get(WorkbookImport, import_id)
    if not imp:
        raise HTTPException(404, "Import not found")
    vendors = db.scalars(select(Vendor).where(Vendor.import_id == import_id).order_by(Vendor.row_number)).all()
    return {"id": imp.id, "filename": imp.filename, "uploaded_at": iso(imp.uploaded_at), "validation": imp.validation,
            "vendors": [vendor_dict(v) for v in vendors]}


# ---------------------------------------------------------------- runs
class RunRequest(BaseModel):
    import_id: str
    vendor_refs: list[str] | None = None


@router.post("/runs")
def create_run(req: RunRequest, db: Session = Depends(get_db), who: str = Depends(actor)):
    try:
        run = start_run(db, req.import_id, vendor_refs=req.vendor_refs, actor=who)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    mode = dispatch(run.id)
    return {"run_id": run.id, "dispatch": mode}


@router.get("/runs")
def list_runs(db: Session = Depends(get_db)):
    rows = db.scalars(select(AssessmentRun).order_by(AssessmentRun.created_at.desc()).limit(50)).all()
    return [_run_dict(r) for r in rows]


def _run_dict(r: AssessmentRun) -> dict:
    return {"id": r.id, "import_id": r.import_id, "status": r.status, "osint_mode": r.osint_mode,
            "search_provider": r.search_provider, "analyzer": r.analyzer, "model_name": r.model_name,
            "prompt_version": r.prompt_version, "methodology_version": r.methodology_version,
            "triggered_by": r.triggered_by, "parent_run_id": r.parent_run_id, "total_vendors": r.total_vendors,
            "completed_vendors": r.completed_vendors, "failed_vendors": r.failed_vendors, "errors": r.errors or [],
            "created_at": iso(r.created_at), "started_at": iso(r.started_at), "completed_at": iso(r.completed_at)}


@router.get("/runs/{run_id}")
def get_run(run_id: str, db: Session = Depends(get_db)):
    run = db.get(AssessmentRun, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    items = []
    for a in db.scalars(select(Assessment).where(Assessment.run_id == run_id)):
        v = db.get(Vendor, a.vendor_id)
        done = {s["stage"] for s in (a.stage_log or [])}
        items.append({**assessment_summary(a), "vendor_ref": v.vendor_ref, "vendor_name": v.name,
                      "stages": [{"key": k, "label": lbl, "done": k in done} for k, lbl in STAGES],
                      "stage_log": a.stage_log or []})
    items.sort(key=lambda x: x["vendor_ref"])
    total_stages = len(STAGES) * max(1, len(items))
    done_stages = sum(sum(s["done"] for s in i["stages"]) for i in items)
    return {**_run_dict(run), "progress": round(done_stages / total_stages, 3), "assessments": items}


# ---------------------------------------------------------------- vendors / assessments
@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), import_id: str | None = None):
    import_id = import_id or current_import_id(db)
    latest = latest_assessments(db, import_id) if import_id else []
    rows = []
    for a in latest:
        v = db.get(Vendor, a.vendor_id)
        rows.append({**assessment_summary(a), "vendor_ref": v.vendor_ref, "vendor_name": v.name,
                     "category": v.category})
    rows.sort(key=lambda r: r["vendor_ref"])
    done = [r for r in rows if r["status"] in ("COMPLETED", "PARTIAL")]
    eff = [r["effective"] for r in done]
    total_vendors = db.scalar(select(func.count(Vendor.id)).where(Vendor.is_example.is_(False),
                                                                 Vendor.import_id == import_id)) or 0
    recent = db.scalars(select(AssessmentRun).order_by(AssessmentRun.created_at.desc()).limit(5)).all()
    imp = db.get(WorkbookImport, import_id) if import_id else None
    return {
        "import": {"id": imp.id, "filename": imp.filename, "uploaded_at": iso(imp.uploaded_at)} if imp else None,
        "totals": {"vendors": total_vendors, "assessed": len(done),
                   "ai_confirmed": sum(e.get("ai_usage") == "YES" for e in eff),
                   "ai_inconclusive": sum(e.get("ai_usage") == "INCONCLUSIVE" for e in eff),
                   "high_critical_risk": sum(e.get("risk_class") in ("HIGH", "CRITICAL") for e in eff),
                   "pending_review": sum(r["review_status"] == "PENDING_REVIEW" for r in done)},
        "criticality_distribution": dict(Counter(e.get("criticality_tier") for e in eff)),
        "risk_distribution": dict(Counter(e.get("risk_class") for e in eff)),
        "vendors": rows,
        "recent_runs": [_run_dict(r) for r in recent],
    }


@router.get("/assessments/{assessment_id}")
def get_assessment(assessment_id: str, db: Session = Depends(get_db)):
    a = db.get(Assessment, assessment_id)
    if not a:
        raise HTTPException(404, "Assessment not found")
    return assessment_detail(db, a)


@router.get("/vendors/{vendor_id}/history")
def vendor_history(vendor_id: str, db: Session = Depends(get_db)):
    v = db.get(Vendor, vendor_id)
    if not v:
        raise HTTPException(404, "Vendor not found")
    same = select(Vendor.id).where(Vendor.vendor_ref == v.vendor_ref)
    rows = db.execute(select(Assessment, AssessmentRun).join(AssessmentRun, AssessmentRun.id == Assessment.run_id)
                      .where(Assessment.vendor_id.in_(same)).order_by(AssessmentRun.created_at.desc())).all()
    return [{**assessment_summary(a), "run_created_at": iso(r.created_at), "methodology_version": r.methodology_version,
             "osint_mode": r.osint_mode} for a, r in rows]


# ---------------------------------------------------------------- evidence / sources
@router.get("/evidence")
def list_evidence(db: Session = Depends(get_db), status: str = Query("VALID"),
                  nature: str | None = None, vendor_ref: str | None = None, latest_only: bool = True):
    ids = [a.id for a in latest_assessments(db, current_import_id(db))] if latest_only else None
    q = select(Evidence)
    if ids is not None:
        q = q.where(Evidence.assessment_id.in_(ids or [""]))
    if status != "ALL":
        q = q.where(Evidence.validation_status == status)
    if nature:
        q = q.where(Evidence.nature == nature)
    out = []
    for e in db.scalars(q):
        a = db.get(Assessment, e.assessment_id)
        v = db.get(Vendor, a.vendor_id)
        if vendor_ref and v.vendor_ref != vendor_ref:
            continue
        out.append(evidence_dict(e, v))
    out.sort(key=lambda e: (e["vendor_ref"] or "", -(e["strength_score"] or 0)))
    return out


@router.get("/sources/{source_id}")
def get_source(source_id: str, db: Session = Depends(get_db)):
    s = db.get(Source, source_id)
    if not s:
        raise HTTPException(404, "Source not found")
    return source_dict(s, include_content=True)


# ---------------------------------------------------------------- review
class ReviewRequest(BaseModel):
    decision: str
    analyst: str = Field(min_length=1, max_length=120)
    reason: str | None = Field(default=None, max_length=4000)
    overrides: dict | None = None


@router.post("/assessments/{assessment_id}/reviews")
def review(assessment_id: str, req: ReviewRequest, db: Session = Depends(get_db)):
    a = db.get(Assessment, assessment_id)
    if not a:
        raise HTTPException(404, "Assessment not found")
    try:
        rv = submit(db, a, decision=req.decision, analyst=req.analyst, reason=req.reason, overrides=req.overrides)
    except ReviewError as exc:
        raise HTTPException(400, str(exc)) from exc
    new_run = None
    if rv.decision == "REQUEST_REASSESSMENT":
        v = db.get(Vendor, a.vendor_id)
        run = db.get(AssessmentRun, a.run_id)
        db.commit()
        new = start_run(db, run.import_id, vendor_refs=[v.vendor_ref], actor=req.analyst, parent_run_id=run.id)
        rv.reassessment_run_id = new.id
        new_run = new.id
        db.commit()
        dispatch(new.id)
    else:
        db.commit()
    return {"review_id": rv.id, "review_status": a.review_status, "reassessment_run_id": new_run}


# ---------------------------------------------------------------- methodology
@router.get("/methodology")
def get_methodology(db: Session = Depends(get_db)):
    m = active_methodology(db)
    row = db.get(MethodologyVersion, m.id)
    versions = db.scalars(select(MethodologyVersion).order_by(MethodologyVersion.created_at.desc())).all()
    return {"active": {"id": row.id, "version": row.version, "label": m.label, "content_hash": row.content_hash,
                       "created_at": iso(row.created_at), "created_by": row.created_by, "note": row.note,
                       "config": row.config, "yaml": row.yaml_text},
            "versions": [{"id": v.id, "version": v.version, "label": f"{v.version}+{v.content_hash[:8]}",
                          "is_active": v.is_active, "created_at": iso(v.created_at), "created_by": v.created_by,
                          "note": v.note} for v in versions]}


class MethodologyUpdate(BaseModel):
    yaml: str = Field(min_length=50, max_length=200_000)
    note: str = Field(min_length=3, max_length=500)


@router.put("/methodology")
def update_methodology(
    req: MethodologyUpdate,
    db: Session = Depends(get_db),
    who: str = Depends(actor),
    _user=Depends(require_role("METHODOLOGY_ADMIN")),
):
    try:
        row = register(db, req.yaml, created_by=who, note=req.note)
    except MethodologyError as exc:
        raise HTTPException(400, str(exc)) from exc
    audit.record(db, "METHODOLOGY_ACTIVATED", actor=who, version=row.version, hash=row.content_hash, note=req.note)
    db.commit()
    return {"id": row.id, "label": f"{row.version}+{row.content_hash[:8]}"}


# ---------------------------------------------------------------- export
def _export_scope(db: Session, import_id: str | None):
    if not import_id:
        imp = db.scalar(select(WorkbookImport).order_by(WorkbookImport.uploaded_at.desc()))
    else:
        imp = db.get(WorkbookImport, import_id)
    if not imp:
        raise HTTPException(404, "No workbook imported yet")
    latest = [a for a in latest_assessments(db, imp.id) if a.status in ("COMPLETED", "PARTIAL")]
    if not latest:
        raise HTTPException(400, "No completed assessments for this workbook")
    return imp, latest


@router.get("/exports/excel")
def export_excel(import_id: str | None = None, db: Session = Depends(get_db), who: str = Depends(actor)):
    imp, latest = _export_scope(db, import_id)
    m = methodology_by_id(db, db.get(AssessmentRun, latest[0].run_id).methodology_version_id)
    data = export_workbook(db, imp, latest, m.config)
    audit.record(db, "EXPORT_EXCEL", actor=who, import_id=imp.id, assessments=[a.id for a in latest])
    db.commit()
    name = imp.filename.rsplit(".", 1)[0] + f"_MAVIRA_{datetime.now(timezone.utc):%Y%m%d}.xlsx"
    return Response(data, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})


@router.get("/exports/json")
def export_json(import_id: str | None = None, db: Session = Depends(get_db), who: str = Depends(actor)):
    imp, latest = _export_scope(db, import_id)
    payload = {"generated_at": datetime.now(timezone.utc).isoformat(), "import": {"id": imp.id, "filename": imp.filename,
               "sha256": imp.file_sha256}, "assessments": [assessment_detail(db, a) for a in latest]}
    audit.record(db, "EXPORT_JSON", actor=who, import_id=imp.id)
    db.commit()
    return Response(json.dumps(payload, indent=2, default=str), media_type="application/json",
                    headers={"Content-Disposition": 'attachment; filename="mavira_assessment.json"'})


# ---------------------------------------------------------------- audit
@router.get("/audit")
def audit_log(db: Session = Depends(get_db), limit: int = Query(200, le=1000), run_id: str | None = None):
    q = select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(limit)
    if run_id:
        q = q.where(AuditEvent.run_id == run_id)
    return [{"id": e.id, "event_type": e.event_type, "actor": e.actor, "run_id": e.run_id,
             "assessment_id": e.assessment_id, "detail": e.detail, "created_at": iso(e.created_at)}
            for e in db.scalars(q)]
