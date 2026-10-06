"""Import + run lifecycle (kept out of the route handlers)."""
from __future__ import annotations

import hashlib
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Assessment, AssessmentRun, Vendor, WorkbookImport
from app.services import audit
from app.services.ingestion.excel_parser import ParseResult, parse_workbook
from app.services.methodology.loader import ensure_active
from app.services.pipeline.orchestrator import describe_analyzer


def create_import(db: Session, filename: str, data: bytes, actor: str = "analyst") -> tuple[WorkbookImport | None, ParseResult]:
    result = parse_workbook(data)
    if not result.valid:
        audit.record(db, "IMPORT_REJECTED", actor=actor, filename=filename, errors=result.errors)
        db.commit()
        return None, result
    sha = hashlib.sha256(data).hexdigest()
    path = Path(get_settings().storage_dir) / f"{sha}.xlsx"
    path.write_bytes(data)
    imp = WorkbookImport(filename=Path(filename).name[:255], file_sha256=sha, stored_path=str(path),
                         sheet_name=result.sheet_name, header_row=result.header_row, column_map=result.column_map,
                         validation=result.report(), vendor_count=len(result.assessable))
    db.add(imp)
    db.flush()
    for pv in result.vendors:
        f = pv.fields
        db.add(Vendor(import_id=imp.id, vendor_ref=f["vendor_ref"], name=f.get("name") or f["vendor_ref"],
                      description=f.get("description"), service=f.get("service"), category=f.get("category"),
                      website=f.get("website"), business_process=f.get("business_process"),
                      operational_dependency=f.get("operational_dependency"),
                      data_classification=f.get("data_classification"), data_volume=f.get("data_volume"),
                      row_number=pv.row_number, is_example=pv.is_example,
                      raw={k: (str(v) if v is not None else None) for k, v in pv.raw.items()}))
    audit.record(db, "IMPORT_ACCEPTED", actor=actor, filename=imp.filename, sha256=sha,
                 vendors=len(result.assessable), warnings=len(result.warnings))
    db.commit()
    return imp, result


def start_run(db: Session, import_id: str, *, vendor_refs: list[str] | None = None, actor: str = "analyst",
              parent_run_id: str | None = None) -> AssessmentRun:
    s = get_settings()
    imp = db.get(WorkbookImport, import_id)
    if not imp:
        raise LookupError("import not found")
    vendors = [v for v in db.scalars(select(Vendor).where(Vendor.import_id == import_id).order_by(Vendor.row_number))
               if not v.is_example and (not vendor_refs or v.vendor_ref in vendor_refs)]
    if not vendors:
        raise ValueError("no assessable vendors in scope")
    mv = ensure_active(db)
    analyzer, model, prompt = describe_analyzer()
    run = AssessmentRun(import_id=import_id, parent_run_id=parent_run_id, status="QUEUED",
                        osint_mode=s.osint_mode.upper(),
                        search_provider=s.search_provider if s.osint_mode.upper() == "LIVE" else "cached-snapshot",
                        analyzer=analyzer, model_name=model, prompt_version=prompt, methodology_version_id=mv.id,
                        methodology_version=f"{mv.version}+{mv.content_hash[:8]}", triggered_by=actor,
                        vendor_scope=[v.vendor_ref for v in vendors], total_vendors=len(vendors), errors=[])
    db.add(run)
    db.flush()
    for v in vendors:
        db.add(Assessment(run_id=run.id, vendor_id=v.id, status="QUEUED", stage_log=[], errors=[]))
    audit.record(db, "RUN_CREATED", actor=actor, run_id=run.id, vendors=run.vendor_scope,
                 methodology=run.methodology_version, osint_mode=run.osint_mode, analyzer=analyzer)
    db.commit()
    return run
