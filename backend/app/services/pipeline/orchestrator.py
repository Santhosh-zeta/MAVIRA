"""Assessment pipeline orchestrator.

criticality -> depth -> search strategy -> source collection -> extraction ->
evidence proposal -> exact-excerpt validation -> strength -> AI usage ->
providers -> risk -> recommendations

One failed source never fails a vendor; one failed vendor never fails the run.
Every stage is persisted as it completes so progress is visible and partial
results survive failures.
"""
from __future__ import annotations

import time
import traceback
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger, run_id_ctx
from app.db.session import SessionLocal
from app.models import (
    AIProvider, AISignal, Assessment, AssessmentRun, AssessmentSource, Evidence, Recommendation, RiskFactor,
    SearchRun, Source, SourceChunk, Vendor,
)
from app.services import audit
from app.services.ai import rule_analyzer
from app.services.ai.llm_analyzer import PROMPT_VERSION, LLMAnalyzer, LLMUnavailable
from app.services.ai.usage import EvidenceView, determine
from app.services.criticality import engine as criticality
from app.services.depth import engine as depth
from app.services.evidence import strength as strength_mod
from app.services.evidence.validator import validate_excerpt
from app.services.extraction import text as textproc
from app.services.extraction.fetcher import Fetcher
from app.services.methodology.loader import Methodology, methodology_by_id
from app.services.osint.providers import SearchError, SearchProvider, get_provider
from app.services.osint.source_classifier import classify, registrable_domain
from app.services.recommendations import engine as rec_engine
from app.services.risk import engine as risk_engine

log = get_logger(__name__)

STAGES = [
    ("profile_loaded", "Vendor profile loaded"),
    ("criticality_calculated", "Criticality calculated"),
    ("depth_selected", "Assessment depth selected"),
    ("search_strategy_generated", "OSINT search strategy generated"),
    ("sources_collected", "Public sources collected"),
    ("content_extracted", "Content extracted and normalised"),
    ("evidence_extracted", "Candidate evidence extracted"),
    ("evidence_validated", "Evidence validated against source text"),
    ("ai_classified", "AI usage classified"),
    ("providers_identified", "AI providers identified"),
    ("risk_calculated", "AI security risk calculated"),
    ("recommendations_generated", "Recommendations generated"),
]
STAGE_LABELS = dict(STAGES)


def vendor_dict(v: Vendor) -> dict:
    return {"vendor_ref": v.vendor_ref, "name": v.name, "description": v.description, "service": v.service,
            "category": v.category, "website": v.website, "business_process": v.business_process,
            "operational_dependency": v.operational_dependency, "data_classification": v.data_classification,
            "data_volume": v.data_volume}


def describe_analyzer() -> tuple[str, str | None, str | None]:
    try:
        a = LLMAnalyzer()
        return a.name, a.model, PROMPT_VERSION
    except LLMUnavailable:
        return f"{rule_analyzer.ANALYZER_NAME}:{rule_analyzer.ANALYZER_VERSION}", None, None


class VendorPipeline:
    def __init__(self, db: Session, run: AssessmentRun, a: Assessment, vendor: Vendor, m: Methodology,
                 provider: SearchProvider, fetcher: Fetcher | None, llm: LLMAnalyzer | None):
        self.db, self.run, self.a, self.v, self.m = db, run, a, vendor, m
        self.provider, self.fetcher, self.llm = provider, fetcher, llm
        self.s = get_settings()
        self.vd = vendor_dict(vendor)
        self.delay = self.s.demo_step_delay_ms / 1000 if run.osint_mode != "LIVE" else 0

    # ------------------------------------------------------------------ utils
    def stage(self, key: str, status: str = "done", **detail) -> None:
        self.a.stage = key
        log_ = list(self.a.stage_log or [])
        log_.append({"stage": key, "label": STAGE_LABELS.get(key, key), "status": status,
                     "at": datetime.now(timezone.utc).isoformat(), **detail})
        self.a.stage_log = log_
        self.db.commit()
        log.info("stage complete", extra={"vendor": self.v.vendor_ref, "stage": key, "status": status})
        if self.delay:
            time.sleep(self.delay)

    def error(self, where: str, msg: str) -> None:
        errs = list(self.a.errors or [])
        errs.append({"stage": where, "error": msg[:500], "at": datetime.now(timezone.utc).isoformat()})
        self.a.errors = errs

    # ------------------------------------------------------------------ run
    def execute(self) -> None:
        a = self.a
        a.status, a.started_at = "RUNNING", datetime.now(timezone.utc)
        self.stage("profile_loaded", vendor=self.v.vendor_ref)

        crit = criticality.calculate(self.vd, self.m)
        a.criticality_score, a.criticality_tier = crit.score, crit.tier
        a.criticality_factors, a.criticality_rationale = crit.to_dict(), crit.rationale
        self.stage("criticality_calculated", tier=crit.tier, score=crit.score)

        plan = depth.plan(crit.tier, self.vd, self.m)
        a.depth_tier, a.depth_plan = plan.tier, {**plan.to_dict(), "description": plan.description()}
        a.human_review_required = plan.human_review_required
        self.stage("depth_selected", tier=plan.tier, categories=len(plan.source_categories))
        self.stage("search_strategy_generated", queries=len(plan.queries))

        links = self.collect(plan)
        self.stage("sources_collected", sources=len(links))

        self.extract(links)
        relevant = sum(l.ai_relevant_chunks > 0 for l in links)
        self.stage("content_extracted", ai_relevant_sources=relevant)

        proposals = self.propose(links)
        self.stage("evidence_extracted", proposals=len(proposals))

        evidence = self.validate(proposals)
        valid = [e for e in evidence if e.validation_status == "VALID"]
        self.stage("evidence_validated", valid=len(valid), rejected=len(evidence) - len(valid))

        views = self.score_strength(valid)
        n_searches = self.db.scalar(select(func.count()).select_from(SearchRun)
                                    .where(SearchRun.assessment_id == a.id)) or 0
        usage = determine(views, self.m, searches=n_searches, sources_checked=len(links),
                          vendor_short=self.short_name())
        a.ai_usage, a.ai_confidence, a.ai_types = usage.usage, usage.confidence, usage.ai_types
        a.ai_usage_summary, a.ai_usage_basis = usage.summary, usage.basis
        a.top_evidence_strength, a.evidence_strength_level = usage.top_strength, usage.top_level
        a.negative_evidence = self.negative_record(links, n_searches, plan, usage)
        self.stage("ai_classified", usage=usage.usage, confidence=usage.confidence)

        providers = self.providers(valid, views)
        status = ("service_linked" if any(p.service_linkage == "SERVICE_LINKED" for p in providers)
                  else "enterprise_level_only" if providers else "not_disclosed")
        a.provider_status = status
        self.stage("providers_identified", providers=[p.provider_name for p in providers], status=status)

        f = crit.factors
        rin = risk_engine.RiskInputs(
            criticality_tier=crit.tier, data_sensitivity=f["data_sensitivity"].score,
            operational_dependency=f["operational_dependency"].score,
            regulatory_exposure=f["regulatory_exposure"].score, ai_usage=usage.usage,
            ai_exposure=usage.ai_exposure, ai_types=usage.ai_types, natures=usage.natures,
            provider_status=status, providers=sorted({p.provider_name for p in providers}),
            service_confirmed=any(v.service_specific and v.nature in self.m["ai_classification"]["confirming_natures"]
                                  for v in views),
            evidence_confidence=usage.confidence)
        risk = risk_engine.calculate(rin, self.m)
        a.risk_score, a.risk_class, a.risk_rationale = risk.score, risk.classification, risk.rationale
        a.risk_inputs = {"inputs": rin.__dict__, "result": risk.to_dict()}
        for c in risk.categories:
            self.db.add(RiskFactor(assessment_id=a.id, category=c.category, score=c.score, weight=c.weight,
                                   contribution=c.contribution, status=c.status, rationale=c.rationale))
        if risk.classification in ("HIGH", "CRITICAL"):
            a.human_review_required = True
        self.stage("risk_calculated", risk=risk.classification, score=risk.score)

        decision = next((c.base for c in risk.categories if c.category == "DECISION_IMPACT"), 0.0)
        rc = rec_engine.RecContext(
            criticality=crit.tier, ai_usage=usage.usage, ai_signal_present=usage.ai_exposure > 0,
            ai_presence=risk.ai_presence, provider_status=status, providers=rin.providers,
            data_sensitivity=f["data_sensitivity"].score, decision_impact=decision,
            decision_types=[t for t in usage.ai_types if self.m["risk"]["decision_impact_by_type"].get(t, 0) >= 0.8],
            natures=usage.natures, evidence_texts={e.id: e.exact_excerpt for e in valid},
            service_short=depth.short_service(self.v.service),
            implements_third_party_platform=bool(rule_analyzer.build_context(self.vd, self.m).partner_terms))
        for r in rec_engine.generate(rc, self.m):
            self.db.add(Recommendation(assessment_id=a.id, rule_id=r.rule_id, priority=r.priority,
                                       category=r.category, action=r.action, due_in_days=r.due_in_days,
                                       grounded_on=r.grounded_on))
        self.stage("recommendations_generated")
        a.status = "PARTIAL" if a.errors else "COMPLETED"
        a.completed_at = datetime.now(timezone.utc)
        self.db.commit()

    def short_name(self) -> str:
        ctx = rule_analyzer.build_context(self.vd, self.m)
        return ctx.aliases[-1] if ctx.aliases else self.v.name

    # ------------------------------------------------------------------ collection
    def collect(self, plan: depth.DepthPlan) -> list[AssessmentSource]:
        links: dict[str, AssessmentSource] = {}
        seen_content: set[str] = set()
        ttl = timedelta(hours=self.s.source_cache_ttl_hours)
        for q in plan.queries:
            if len(links) >= plan.max_sources:
                break
            t0 = time.monotonic()
            sr = SearchRun(assessment_id=self.a.id, category=q.category, query=q.query,
                           provider=self.provider.name, status="OK")
            try:
                hits = self.provider.search(q.query, category=q.category, vendor_ref=self.v.vendor_ref)
                sr.result_count = len(hits)
            except (SearchError, Exception) as exc:  # noqa: BLE001 - provider failures must not stop the vendor
                hits = []
                sr.status, sr.error = "FAILED", f"{type(exc).__name__}: {exc}"[:400]
                self.error("sources_collected", f"search failed for '{q.query}': {sr.error}")
            sr.latency_ms = int((time.monotonic() - t0) * 1000)
            self.db.add(sr)
            for hit in hits:
                if len(links) >= plan.max_sources:
                    break
                uh = textproc.url_hash(hit.url)
                if uh in links:
                    continue
                try:
                    src, from_cache = self.get_or_create_source(hit, uh, q.category, ttl)
                except Exception as exc:  # noqa: BLE001
                    self.error("sources_collected", f"{hit.url}: {type(exc).__name__}")
                    continue
                if src.content_hash and src.content_hash in seen_content:
                    continue                                  # duplicate content under another URL
                if src.content_hash:
                    seen_content.add(src.content_hash)
                link = AssessmentSource(assessment_id=self.a.id, source_id=src.id, category=q.category,
                                        from_cache=from_cache)
                link.source = src
                self.db.add(link)
                links[uh] = link
        self.db.flush()
        return list(links.values())

    def get_or_create_source(self, hit, uh: str, category: str, ttl: timedelta) -> tuple[Source, bool]:
        existing = self.db.scalar(select(Source).where(Source.url_hash == uh))
        now = datetime.now(timezone.utc)
        if existing and existing.status == "OK" and existing.content:
            ra = existing.retrieved_at
            if ra and ra.tzinfo is None:
                ra = ra.replace(tzinfo=timezone.utc)
            fresh = existing.collection_method != "LIVE" or (ra and now - ra < ttl)
            if fresh:
                return existing, True
        sc = classify(hit.url, self.v.website, self.m, category_hint=category)
        src = existing or Source(url=hit.url, url_hash=uh)
        src.domain = registrable_domain((hit.url.split("/")[2] if "://" in hit.url else hit.url))
        src.source_type, src.reliability_level, src.reliability_score = sc.source_type, sc.level, sc.score
        if hit.content is not None:                              # CACHED snapshot or DEMO_MOCK fixture
            src.title, src.content = hit.title, textproc.clean(hit.content)
            src.collection_method, src.cache_origin = hit.collection_method, hit.cache_origin
            src.retrieved_at = _parse_dt(hit.retrieved_at) or now
            src.published_date = _parse_date(hit.published_date)
            src.status = "OK"
        else:                                                    # LIVE fetch
            if not self.fetcher:
                raise RuntimeError("live fetcher unavailable")
            fr = self.fetcher.fetch(hit.url, etag=existing.etag if existing else None,
                                    last_modified=existing.last_modified if existing else None)
            src.collection_method, src.retrieved_at, src.http_status = "LIVE", now, fr.http_status
            if fr.status == "NOT_MODIFIED" and existing:
                return existing, True
            src.status, src.error = fr.status, fr.error
            src.title = fr.title or hit.title
            src.content = textproc.clean(fr.text) if fr.text else None
            src.etag, src.last_modified = fr.etag, fr.last_modified
            src.published_date = _parse_date(fr.published_date)
            if fr.status != "OK":
                self.error("sources_collected", f"{hit.url}: {fr.status} {fr.error or ''}".strip())
        src.content_hash = textproc.content_hash(src.content) if src.content else None
        if not existing:
            self.db.add(src)
        self.db.flush()
        return src, False

    def extract(self, links: list[AssessmentSource]) -> None:
        for link in links:
            src = link.source
            if not src.content:
                continue
            if not src.chunks:
                for ch in textproc.chunk(src.content):
                    src.chunks.append(SourceChunk(idx=ch.idx, text=ch.text, char_start=ch.char_start,
                                                  ai_relevant=ch.ai_relevant))
            link.ai_relevant_chunks = sum(1 for c in src.chunks if c.ai_relevant)
        self.db.flush()

    # ------------------------------------------------------------------ evidence
    def propose(self, links: list[AssessmentSource]):
        ctx = rule_analyzer.build_context(self.vd, self.m)
        out = []
        for link in links:
            src = link.source
            if not src.content or link.ai_relevant_chunks == 0:
                continue
            official = src.source_type is not None and src.source_type.startswith(("official_", "vendor_", "investor_"))
            props, by = None, "rule-based"
            if self.llm:
                try:
                    props, meta = self.llm.propose(src.content, src.title or "", ctx, official=official,
                                                   source_type=src.source_type or "", methodology=self.m)
                    by = self.llm.name
                    log.info("llm proposals", extra={"vendor": self.v.vendor_ref, "source": src.url,
                                                     "model": meta.get("model"), "latency_ms": meta.get("latency_ms")})
                except Exception as exc:  # noqa: BLE001 - LLM failure falls back to rules
                    self.error("evidence_extracted", f"LLM failed on {src.url}: {type(exc).__name__}; rule-based fallback used")
            if props is None:
                props = rule_analyzer.analyze_source(src.content, src.title or "", ctx, official=official,
                                                     source_type=src.source_type or "", methodology=self.m)
            out.extend((src, p, by) for p in props)
        return out

    def validate(self, proposals) -> list[Evidence]:
        rows = []
        for src, p, by in proposals:
            vr = validate_excerpt(p.exact_excerpt, src.content)
            ev = Evidence(assessment_id=self.a.id, source_id=src.id, claim=p.claim, exact_excerpt=p.exact_excerpt,
                          excerpt_start=vr.start, excerpt_end=vr.end,
                          validation_status="VALID" if vr.valid else "REJECTED", rejection_reason=vr.reason,
                          nature=p.nature, ai_types=p.ai_types, interpretation=p.interpretation,
                          directness=p.directness, service_relevance=p.service_relevance, confidence=p.confidence,
                          proposed_by=by)
            ev.source = src
            ev._proposal = p                      # transient, not persisted
            self.db.add(ev)
            rows.append(ev)
        self.db.flush()
        return rows

    def score_strength(self, valid: list[Evidence]) -> list[EvidenceView]:
        weights = self.m["ai_classification"]["nature_weights"]
        as_of = date.today()
        type_domains: dict[str, set[str]] = {}
        for e in valid:
            if weights.get(e.nature, 0) > 0:
                for t in e.ai_types or []:
                    type_domains.setdefault(t, set()).add(e.source.domain)
        views = []
        for e in valid:
            p = e._proposal
            corroborated = any(len(type_domains.get(t, set()) - {e.source.domain}) > 0
                               for t in (e.ai_types or []) if t != "Unknown")
            sc, lvl, br = strength_mod.score(strength_mod.StrengthInputs(
                reliability_score=e.source.reliability_score or 0.25, directness=e.directness or "commentary",
                excerpt=e.exact_excerpt, ai_types=e.ai_types or [], provider_count=len(p.providers),
                service_relevance=e.service_relevance or 0.0, corroborated=corroborated,
                published=e.source.published_date, as_of=as_of), self.m)
            e.strength_score, e.strength_level, e.strength_breakdown = sc, lvl, br
            exp = weights.get(e.nature, 0) * sc / 100
            for t in e.ai_types or ["Unknown"]:
                self.db.add(AISignal(assessment_id=self.a.id, evidence_id=e.id, nature=e.nature, ai_type=t,
                                     exposure=round(exp, 3)))
            views.append(EvidenceView(id=e.id, source_id=e.source_id, domain=e.source.domain, nature=e.nature,
                                      ai_types=e.ai_types or [], strength=sc, level=lvl,
                                      reliability_level=e.source.reliability_level or "LOW", excerpt=e.exact_excerpt,
                                      negative=p.negative_statement, service_specific=p.service_specific))
        self.db.flush()
        return views

    def providers(self, valid: list[Evidence], views: list[EvidenceView]) -> list[AIProvider]:
        best: dict[str, AIProvider] = {}
        for e in valid:
            p = e._proposal
            if e.nature in ("INDUSTRY_COMMENTARY", "MARKETING_ONLY"):
                continue
            for prov in p.providers:
                link = "SERVICE_LINKED" if p.service_specific else "ENTERPRISE_LEVEL_ONLY"
                conf = round(min(0.95, (e.strength_score or 0) / 100 * (1.0 if link == "SERVICE_LINKED" else 0.85)), 2)
                cur = best.get(prov.name)
                if not cur or conf > cur.confidence:
                    best[prov.name] = AIProvider(assessment_id=self.a.id, evidence_id=e.id, provider_name=prov.name,
                                                 provider_type=prov.type, confidence=conf, service_linkage=link,
                                                 evidence_excerpt=e.exact_excerpt)
        for row in best.values():
            self.db.add(row)
        self.db.flush()
        return list(best.values())

    def negative_record(self, links, n_searches: int, plan: depth.DepthPlan, usage) -> dict:
        checked = [{"url": l.source.url, "title": l.source.title, "status": l.source.status,
                    "collection_method": l.source.collection_method, "reliability": l.source.reliability_level,
                    "ai_relevant_chunks": l.ai_relevant_chunks} for l in links]
        statement = None
        if usage.ai_exposure == 0:
            statement = self.m["ai_classification"]["no_evidence_statement"]
        no_ai = [c["url"] for c in checked if c["ai_relevant_chunks"] == 0]
        return {"sources_checked": len(checked), "searches_performed": n_searches,
                "assessment_scope": plan.source_categories, "sources": checked,
                "sources_without_ai_content": no_ai, "statement": statement,
                "negative_review_required": plan.negative_evidence_review}


def _parse_dt(v: str | None) -> datetime | None:
    if not v:
        return None
    try:
        d = datetime.fromisoformat(v)
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _parse_date(v: str | None) -> date | None:
    if not v:
        return None
    try:
        return date.fromisoformat(str(v)[:10])
    except ValueError:
        return None


def run_assessment(run_id: str, provider: SearchProvider | None = None) -> None:
    """Entry point for the worker / background thread."""
    token = run_id_ctx.set(run_id)
    db = SessionLocal()
    try:
        run = db.get(AssessmentRun, run_id)
        if not run:
            log.error("run not found")
            return
        m = methodology_by_id(db, run.methodology_version_id)
        provider = provider or get_provider()
        fetcher = Fetcher() if run.osint_mode == "LIVE" else None
        try:
            llm = LLMAnalyzer()
        except LLMUnavailable:
            llm = None
        run.status, run.started_at = "RUNNING", datetime.now(timezone.utc)
        audit.record(db, "RUN_STARTED", run_id=run.id, osint_mode=run.osint_mode, analyzer=run.analyzer)
        db.commit()
        assessments = list(db.scalars(select(Assessment).where(Assessment.run_id == run.id)))
        for a in assessments:
            vendor = db.get(Vendor, a.vendor_id)
            try:
                VendorPipeline(db, run, a, vendor, m, provider, fetcher, llm).execute()
                run.completed_vendors += 1
                audit.record(db, "VENDOR_ASSESSED", run_id=run.id, assessment_id=a.id, vendor=vendor.vendor_ref,
                             criticality=a.criticality_tier, ai_usage=a.ai_usage, risk=a.risk_class)
            except Exception as exc:  # noqa: BLE001 - isolate vendor failures
                db.rollback()
                a = db.get(Assessment, a.id)
                a.status = "FAILED"
                a.errors = list(a.errors or []) + [{"stage": a.stage, "error": f"{type(exc).__name__}: {exc}"[:500]}]
                run.failed_vendors += 1
                run.errors = list(run.errors or []) + [{"vendor": vendor.vendor_ref, "error": f"{type(exc).__name__}: {exc}"[:300]}]
                log.error("vendor failed", extra={"vendor": vendor.vendor_ref, "error": traceback.format_exc()[-800:]})
                audit.record(db, "VENDOR_FAILED", run_id=run.id, assessment_id=a.id, vendor=vendor.vendor_ref,
                             error=str(exc)[:300])
            db.commit()
        run.status = ("COMPLETED" if run.failed_vendors == 0 and not any(x.status == "PARTIAL" for x in assessments)
                      else "PARTIAL" if run.completed_vendors else "FAILED")
        run.completed_at = datetime.now(timezone.utc)
        audit.record(db, "RUN_COMPLETED", run_id=run.id, status=run.status, completed=run.completed_vendors,
                     failed=run.failed_vendors)
        db.commit()
    except Exception:  # noqa: BLE001
        db.rollback()
        run = db.get(AssessmentRun, run_id)
        if run:
            run.status = "FAILED"
            run.errors = list(run.errors or []) + [{"error": traceback.format_exc()[-500:]}]
            db.commit()
        log.exception("run failed")
    finally:
        db.close()
        run_id_ctx.reset(token)
