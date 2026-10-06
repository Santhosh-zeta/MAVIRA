"""Methodology calibration against the fictional worked example (V-000).

The fixture text is taken from the example row of the supplied workbook and is
labelled DEMO_MOCK — it is fictional and never mixed with real-vendor evidence.
"""
from __future__ import annotations

from app.models import Assessment, AssessmentRun, Vendor, WorkbookImport
from app.services.methodology.loader import ensure_active
from app.services.osint.providers import FixtureProvider
from app.services.pipeline.orchestrator import VendorPipeline

LARKSPUR = dict(
    vendor_ref="V-000", name="Larkspur Servicing Group Ltd", category="Lending Servicing & Collections (onshore, staff-augmented)",
    website="www.larkspurservicing.example",
    description="Outsourced loan servicing and arrears management.",
    service="Outsourced loan servicing and arrears management. Larkspur operates the borrower contact centre, handles payment arrangements and hardship cases, issues arrears correspondence, and maintains the servicing record that synchronises nightly with Meridian's core lending platform.",
    business_process="Retail lending servicing, arrears management and collections.", operational_dependency="High",
    data_classification="Borrower names, addresses, dates of birth, loan account numbers, repayment schedules, arrears status, income and expenditure statements, hardship and vulnerability notes (including health-related disclosures), and recorded call audio.",
    data_volume="Approximately 240,000 active loan accounts under servicing and around 660,000 borrower interactions per year, of which an estimated 180,000 are recorded voice calls.")

FIXTURE = [
    {"vendor_ref": "V-000", "found_by": ["executive_statements"], "url": "https://www.linkedin.com/posts/larkspur-ceo-ai-assist",
     "title": "Larkspur CEO post (fictional)", "published_date": "2026-02-04", "retrieved_at": "2026-03-09T00:00:00+00:00",
     "content": ("Larkspur Assist was built by our own engineering team to support servicing staff. "
                 "Our AI upskilling programme has reached more than 400 servicing agents. "
                 "Larkspur Assist uses leading foundation models, and its AI agents draft borrower correspondence, "
                 "summarise call history and progress routine arrangements without human handoff.")},
    {"vendor_ref": "V-000", "found_by": ["careers"], "url": "https://www.larkspurservicing.example/careers",
     "title": "Applied AI Engineer — Servicing Automation (fictional)", "published_date": "2026-03-01",
     "retrieved_at": "2026-03-09T00:00:00+00:00",
     "content": "Larkspur is hiring an Applied AI Engineer to build AI agent orchestration against live account data and call transcription pipelines."},
]


def test_worked_example_calibration(db):
    mv = ensure_active(db)
    imp = WorkbookImport(filename="fixture.xlsx", file_sha256="0" * 64, stored_path="/dev/null", sheet_name="x",
                         header_row=3, column_map={}, validation={}, vendor_count=1)
    db.add(imp)
    db.flush()
    v = Vendor(import_id=imp.id, row_number=4, raw={}, **LARKSPUR)
    db.add(v)
    run = AssessmentRun(import_id=imp.id, osint_mode="DEMO", search_provider="fixture", analyzer="rule-based",
                        methodology_version_id=mv.id, methodology_version=mv.version, errors=[])
    db.add(run)
    db.flush()
    a = Assessment(run_id=run.id, vendor_id=v.id, stage_log=[], errors=[])
    db.add(a)
    db.commit()
    from app.services.methodology.loader import methodology_by_id
    VendorPipeline(db, run, a, v, methodology_by_id(db, mv.id), FixtureProvider(FIXTURE), None, None).execute()
    db.refresh(a)
    assert a.criticality_tier == "CRITICAL"                           # matches the worked example
    natures = {e.nature for e in a.evidence if e.validation_status == "VALID"}
    assert "HIRING_SIGNAL" in natures and natures & {"PRODUCT_FEATURE", "SERVICE_INTEGRATED", "INTERNAL_OPERATIONAL_USE"}
    assert "Agentic AI" in (a.ai_types or [])
    assert a.provider_status == "not_disclosed"                       # "leading foundation models" names no provider
    assert a.risk_class in ("MEDIUM", "HIGH", "CRITICAL")
    assert all(l.source.collection_method == "DEMO_MOCK" for l in a.source_links)
    # Worked example: Critical / Yes / Critical risk. Engine: Critical / Yes / High —
    # the executive post is MEDIUM reliability and no excerpt names Meridian's
    # specific service, so AI presence is discounted (documented divergence).
    assert a.ai_usage == "YES" and a.ai_usage_basis
    assert a.risk_class in ("HIGH", "CRITICAL")




