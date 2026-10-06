"""Relational model. Assessments are append-only: a re-assessment creates a new
run + assessment rows, and analyst reviews never overwrite generated results."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (
    JSON, Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _id() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


class MethodologyVersion(Base):
    __tablename__ = "methodology_versions"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    version: Mapped[str] = mapped_column(String(32))
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    config: Mapped[dict] = mapped_column(JSON)
    yaml_text: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_by: Mapped[str] = mapped_column(String(120), default="system")
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class WorkbookImport(Base):
    __tablename__ = "workbook_imports"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    filename: Mapped[str] = mapped_column(String(255))
    file_sha256: Mapped[str] = mapped_column(String(64), index=True)
    stored_path: Mapped[str] = mapped_column(String(500))
    sheet_name: Mapped[str] = mapped_column(String(120))
    header_row: Mapped[int] = mapped_column(Integer)
    column_map: Mapped[dict] = mapped_column(JSON)
    validation: Mapped[dict] = mapped_column(JSON)
    vendor_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(24), default="VALIDATED")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    vendors: Mapped[list["Vendor"]] = relationship(back_populates="workbook_import")


class Vendor(Base):
    __tablename__ = "vendors"
    __table_args__ = (UniqueConstraint("import_id", "vendor_ref", name="uq_vendor_import_ref"),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    import_id: Mapped[str] = mapped_column(ForeignKey("workbook_imports.id", ondelete="CASCADE"), index=True)
    vendor_ref: Mapped[str] = mapped_column(String(32), index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    service: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(120))
    website: Mapped[str | None] = mapped_column(String(255))
    business_process: Mapped[str | None] = mapped_column(Text)
    operational_dependency: Mapped[str | None] = mapped_column(String(40))
    data_classification: Mapped[str | None] = mapped_column(Text)
    data_volume: Mapped[str | None] = mapped_column(Text)
    row_number: Mapped[int] = mapped_column(Integer)
    is_example: Mapped[bool] = mapped_column(Boolean, default=False)
    raw: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    workbook_import: Mapped[WorkbookImport] = relationship(back_populates="vendors")


class AssessmentRun(Base):
    __tablename__ = "assessment_runs"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    import_id: Mapped[str] = mapped_column(ForeignKey("workbook_imports.id", ondelete="CASCADE"), index=True)
    parent_run_id: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(24), default="QUEUED", index=True)
    osint_mode: Mapped[str] = mapped_column(String(16))
    search_provider: Mapped[str] = mapped_column(String(32))
    analyzer: Mapped[str] = mapped_column(String(80))
    model_name: Mapped[str | None] = mapped_column(String(120))
    prompt_version: Mapped[str | None] = mapped_column(String(40))
    methodology_version_id: Mapped[str] = mapped_column(ForeignKey("methodology_versions.id"))
    methodology_version: Mapped[str] = mapped_column(String(64))
    triggered_by: Mapped[str] = mapped_column(String(120), default="analyst")
    vendor_scope: Mapped[list | None] = mapped_column(JSON)
    total_vendors: Mapped[int] = mapped_column(Integer, default=0)
    completed_vendors: Mapped[int] = mapped_column(Integer, default=0)
    failed_vendors: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    assessments: Mapped[list["Assessment"]] = relationship(back_populates="run")


class Assessment(Base):
    __tablename__ = "assessments"
    __table_args__ = (UniqueConstraint("run_id", "vendor_id", name="uq_assessment_run_vendor"),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    run_id: Mapped[str] = mapped_column(ForeignKey("assessment_runs.id", ondelete="CASCADE"), index=True)
    vendor_id: Mapped[str] = mapped_column(ForeignKey("vendors.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(24), default="QUEUED", index=True)
    stage: Mapped[str | None] = mapped_column(String(48))
    stage_log: Mapped[list] = mapped_column(JSON, default=list)
    # criticality
    criticality_score: Mapped[float | None] = mapped_column(Float)
    criticality_tier: Mapped[str | None] = mapped_column(String(16), index=True)
    criticality_factors: Mapped[dict | None] = mapped_column(JSON)
    criticality_rationale: Mapped[str | None] = mapped_column(Text)
    # depth
    depth_tier: Mapped[str | None] = mapped_column(String(16))
    depth_plan: Mapped[dict | None] = mapped_column(JSON)
    # AI usage
    ai_usage: Mapped[str | None] = mapped_column(String(16), index=True)
    ai_confidence: Mapped[float | None] = mapped_column(Float)
    ai_types: Mapped[list | None] = mapped_column(JSON)
    ai_usage_summary: Mapped[str | None] = mapped_column(Text)
    ai_usage_basis: Mapped[str | None] = mapped_column(Text)
    provider_status: Mapped[str | None] = mapped_column(String(32))
    negative_evidence: Mapped[dict | None] = mapped_column(JSON)
    evidence_strength_level: Mapped[str | None] = mapped_column(String(16))
    top_evidence_strength: Mapped[float | None] = mapped_column(Float)
    # risk
    risk_score: Mapped[float | None] = mapped_column(Float)
    risk_class: Mapped[str | None] = mapped_column(String(20), index=True)
    risk_rationale: Mapped[str | None] = mapped_column(Text)
    risk_inputs: Mapped[dict | None] = mapped_column(JSON)
    # workflow
    human_review_required: Mapped[bool] = mapped_column(Boolean, default=False)
    review_status: Mapped[str] = mapped_column(String(32), default="PENDING_REVIEW")
    errors: Mapped[list] = mapped_column(JSON, default=list)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    run: Mapped[AssessmentRun] = relationship(back_populates="assessments")
    vendor: Mapped[Vendor] = relationship()
    evidence: Mapped[list["Evidence"]] = relationship(back_populates="assessment", cascade="all, delete-orphan")
    providers: Mapped[list["AIProvider"]] = relationship(cascade="all, delete-orphan")
    risk_factors: Mapped[list["RiskFactor"]] = relationship(cascade="all, delete-orphan")
    recommendations: Mapped[list["Recommendation"]] = relationship(cascade="all, delete-orphan")
    reviews: Mapped[list["AnalystReview"]] = relationship(cascade="all, delete-orphan", order_by="AnalystReview.created_at")
    search_runs: Mapped[list["SearchRun"]] = relationship(cascade="all, delete-orphan")
    source_links: Mapped[list["AssessmentSource"]] = relationship(cascade="all, delete-orphan")


class SearchRun(Base):
    __tablename__ = "search_runs"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    assessment_id: Mapped[str] = mapped_column(ForeignKey("assessments.id", ondelete="CASCADE"), index=True)
    category: Mapped[str] = mapped_column(String(48))
    query: Mapped[str] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(24))
    result_count: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(Text)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Source(Base):
    __tablename__ = "sources"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    url: Mapped[str] = mapped_column(Text)
    url_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    domain: Mapped[str] = mapped_column(String(255), index=True)
    title: Mapped[str | None] = mapped_column(Text)
    source_type: Mapped[str | None] = mapped_column(String(64))
    reliability_level: Mapped[str | None] = mapped_column(String(16))
    reliability_score: Mapped[float | None] = mapped_column(Float)
    published_date: Mapped[date | None] = mapped_column(Date)
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    content: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    collection_method: Mapped[str] = mapped_column(String(16))   # LIVE | CACHED | DEMO_MOCK
    cache_origin: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(24), default="OK")
    http_status: Mapped[int | None] = mapped_column(Integer)
    etag: Mapped[str | None] = mapped_column(String(255))
    last_modified: Mapped[str | None] = mapped_column(String(64))
    error: Mapped[str | None] = mapped_column(Text)
    chunks: Mapped[list["SourceChunk"]] = relationship(cascade="all, delete-orphan", order_by="SourceChunk.idx")


class AssessmentSource(Base):
    __tablename__ = "assessment_sources"
    __table_args__ = (UniqueConstraint("assessment_id", "source_id", name="uq_assessment_source"),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    assessment_id: Mapped[str] = mapped_column(ForeignKey("assessments.id", ondelete="CASCADE"), index=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), index=True)
    category: Mapped[str | None] = mapped_column(String(48))
    from_cache: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_relevant_chunks: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[Source] = relationship()


class SourceChunk(Base):
    __tablename__ = "source_chunks"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), index=True)
    idx: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    char_start: Mapped[int] = mapped_column(Integer)
    ai_relevant: Mapped[bool] = mapped_column(Boolean, default=False)


class Evidence(Base):
    __tablename__ = "evidence"
    __table_args__ = (Index("ix_evidence_assessment_status", "assessment_id", "validation_status"),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    assessment_id: Mapped[str] = mapped_column(ForeignKey("assessments.id", ondelete="CASCADE"), index=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), index=True)
    claim: Mapped[str] = mapped_column(Text)
    exact_excerpt: Mapped[str] = mapped_column(Text)
    excerpt_start: Mapped[int | None] = mapped_column(Integer)
    excerpt_end: Mapped[int | None] = mapped_column(Integer)
    validation_status: Mapped[str] = mapped_column(String(16))     # VALID | REJECTED
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    nature: Mapped[str | None] = mapped_column(String(32))
    ai_types: Mapped[list | None] = mapped_column(JSON)
    interpretation: Mapped[str | None] = mapped_column(Text)
    directness: Mapped[str | None] = mapped_column(String(32))
    service_relevance: Mapped[float | None] = mapped_column(Float)
    strength_score: Mapped[float | None] = mapped_column(Float)
    strength_level: Mapped[str | None] = mapped_column(String(16))
    strength_breakdown: Mapped[dict | None] = mapped_column(JSON)
    confidence: Mapped[float | None] = mapped_column(Float)
    proposed_by: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    assessment: Mapped[Assessment] = relationship(back_populates="evidence")
    source: Mapped[Source] = relationship()
    signals: Mapped[list["AISignal"]] = relationship(cascade="all, delete-orphan")


class AISignal(Base):
    __tablename__ = "ai_signals"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    assessment_id: Mapped[str] = mapped_column(ForeignKey("assessments.id", ondelete="CASCADE"), index=True)
    evidence_id: Mapped[str] = mapped_column(ForeignKey("evidence.id", ondelete="CASCADE"), index=True)
    nature: Mapped[str] = mapped_column(String(32))
    ai_type: Mapped[str] = mapped_column(String(48))
    exposure: Mapped[float] = mapped_column(Float)


class AIProvider(Base):
    __tablename__ = "ai_providers"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    assessment_id: Mapped[str] = mapped_column(ForeignKey("assessments.id", ondelete="CASCADE"), index=True)
    evidence_id: Mapped[str] = mapped_column(ForeignKey("evidence.id", ondelete="CASCADE"))
    provider_name: Mapped[str] = mapped_column(String(120))
    provider_type: Mapped[str] = mapped_column(String(48))
    confidence: Mapped[float] = mapped_column(Float)
    service_linkage: Mapped[str] = mapped_column(String(32))
    evidence_excerpt: Mapped[str] = mapped_column(Text)


class RiskFactor(Base):
    __tablename__ = "risk_factors"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    assessment_id: Mapped[str] = mapped_column(ForeignKey("assessments.id", ondelete="CASCADE"), index=True)
    category: Mapped[str] = mapped_column(String(40))
    score: Mapped[float] = mapped_column(Float)
    weight: Mapped[float] = mapped_column(Float)
    contribution: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(40))
    rationale: Mapped[str] = mapped_column(Text)


class Recommendation(Base):
    __tablename__ = "recommendations"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    assessment_id: Mapped[str] = mapped_column(ForeignKey("assessments.id", ondelete="CASCADE"), index=True)
    rule_id: Mapped[str] = mapped_column(String(64))
    priority: Mapped[str] = mapped_column(String(4))
    category: Mapped[str] = mapped_column(String(32))
    action: Mapped[str] = mapped_column(Text)
    due_in_days: Mapped[int] = mapped_column(Integer)
    grounded_on: Mapped[dict] = mapped_column(JSON)


class AnalystReview(Base):
    __tablename__ = "analyst_reviews"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    assessment_id: Mapped[str] = mapped_column(ForeignKey("assessments.id", ondelete="CASCADE"), index=True)
    decision: Mapped[str] = mapped_column(String(32))     # APPROVE | OVERRIDE | REQUEST_REASSESSMENT
    analyst: Mapped[str] = mapped_column(String(120))
    reason: Mapped[str | None] = mapped_column(Text)
    overrides: Mapped[dict | None] = mapped_column(JSON)
    original_snapshot: Mapped[dict] = mapped_column(JSON)
    reassessment_run_id: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    run_id: Mapped[str | None] = mapped_column(String(32), index=True)
    assessment_id: Mapped[str | None] = mapped_column(String(32), index=True)
    actor: Mapped[str] = mapped_column(String(120))
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
