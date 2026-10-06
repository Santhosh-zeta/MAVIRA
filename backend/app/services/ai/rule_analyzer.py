"""Deterministic AI-signal analyzer (default; no data leaves the environment).

Proposes evidence sentence-by-sentence from source text and classifies the
nature of each signal using transparent linguistic cues. Output conforms to the
same `EvidenceProposal` schema the LLM analyzer must produce.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.schemas.llm import EvidenceProposal, ProposedProvider
from app.services.ai import lexicon as L
from app.services.extraction.text import sentences

ANALYZER_NAME = "rule-based"
ANALYZER_VERSION = "rules-v1.0"


@dataclass
class VendorContext:
    vendor_ref: str
    name: str
    aliases: list[str]
    category: str
    service: str
    description: str
    service_specific_terms: list[str]
    category_keywords: list[str]
    partner_terms: list[str]


_STOP = {"The", "A", "An", "Including", "And", "Of", "Services", "Service", "Platform"}
_GENERIC_WORDS = {
    "platform", "system", "systems", "supporting", "support", "services", "service", "customer", "customers",
    "management", "operations", "including", "provided", "provides", "related", "multiple", "sources",
    "activities", "enterprise", "across", "within", "meridian", "other", "facilitating", "financial",
    "institutions", "solution", "solutions", "estate", "delegated", "authority", "outsourced", "onshore",
    "maintains", "operates", "handles", "issues", "record", "nightly", "staff", "network", "infrastructure",
    "produces", "distributes", "hosts", "processing", "real-time", "modernization", "implementation",
}
_COMMON_FIRST = {"the", "financial", "global", "first", "national", "american", "bank", "data", "united",
                 "general", "international", "payments", "technology", "technologies", "services"}


def build_context(vendor: dict, methodology) -> VendorContext:
    name = (vendor.get("name") or "").strip()
    base = re.sub(r"\(.*?\)", "", name).replace(", Inc.", "").replace(" Inc.", "").replace(" L.L.C.", "").strip(" ,.")
    aliases = {base}
    first = base.split()[0] if base else ""
    if first and first.lower() not in _COMMON_FIRST:
        aliases.add(first)
    paren = re.findall(r"\(([^)]+)\)", name)
    aliases.update(paren)
    if base.lower().startswith("the "):
        aliases.add(" ".join(base.split()[1:3]))           # "Clearing House"
    if "clearing house" in base.lower():
        aliases.add("TCH")
    aliases = sorted({a for a in aliases if len(a) >= 3}, key=len, reverse=True)

    service = vendor.get("service") or ""
    specific = set(re.findall(r"\b[A-Z]{2,}\b", service))                  # DNA, RTP, IRS, ACH
    specific.update(m.strip() for m in re.findall(r"\b(?:[A-Z][a-z]+ ){1,3}(?:[A-Z][a-z]+)\b", service)
                    if m.split()[0] not in _STOP)
    specific = sorted(s for s in specific if s.lower() not in {a.lower() for a in aliases})

    desc = vendor.get("description") or ""
    partner = []
    m = re.search(r"including (.+?)(?: software| solutions| services|\.|$)", desc)
    if m:
        partner = [t.strip() for t in re.split(r",| and ", m.group(1)) if t.strip() and t.strip()[0].isupper()]

    cat = (vendor.get("category") or "").lower()
    kw = list(methodology["ai_classification"]["category_service_keywords"].get(cat, []))
    # plus distinctive words from the contracted service / process description
    svc_words = re.findall(r"[a-z][a-z\-]{5,}", f"{service} {vendor.get('business_process') or ''}".lower())
    kw += sorted({w for w in svc_words if w not in _GENERIC_WORDS and w not in kw})
    return VendorContext(vendor_ref=vendor.get("vendor_ref") or "", name=name, aliases=aliases, category=cat,
                         service=service, description=desc, service_specific_terms=specific,
                         category_keywords=kw, partner_terms=partner)


def _mentions(text: str, terms: list[str]) -> list[str]:
    out = []
    for t in terms:
        if re.search(rf"(?<![A-Za-z]){re.escape(t)}(?![A-Za-z])", text, re.I if len(t) > 3 else 0):
            out.append(t)
    return out


def service_relevance(text: str, ctx: VendorContext, cap: float) -> tuple[float, list[str], bool]:
    low = text.lower()
    hits = [k for k in ctx.category_keywords if re.search(rf"\b{re.escape(k)}", low)]
    rel = min(1.0, 0.25 * len(hits))
    specific = _mentions(text, ctx.service_specific_terms)
    if specific:
        rel = min(1.0, max(rel, 0.7) + 0.2)
    else:
        rel = min(rel, cap)
    return round(rel, 3), hits + specific, bool(specific)


def classify_sentence(sentence: str, paragraph: str, title: str, ctx: VendorContext, *, official: bool,
                      source_type: str, cap: float, svc_min: float) -> EvidenceProposal | None:
    if not L.has_ai_term(sentence):
        return None
    vendor_named = bool(_mentions(paragraph, ctx.aliases))
    first_person = bool(L.FIRST_PERSON.search(sentence)) and official
    self_ref = vendor_named or first_person
    partner_hits = _mentions(paragraph + " " + title, ctx.partner_terms)
    ai_types = L.ai_types_in(sentence)
    providers = [ProposedProvider(**p) for p in L.providers_in(sentence)] if self_ref else []
    rel, rel_terms, specific = service_relevance(sentence, ctx, cap)
    cues: list[str] = []

    if L.NEGATIVE_USE.search(sentence) and self_ref:
        nature, conf = "UNKNOWN", 0.8
        cues.append("explicit negative statement about AI use")
        directness = "vendor_self_statement" if official else "third_party_about_vendor"
        return EvidenceProposal(exact_excerpt=sentence, claim=f"{ctx.name} states it does not use AI",
                                nature=nature, ai_types=ai_types, providers=[], directness=directness,
                                service_relevance=rel, relevance_terms=rel_terms, service_specific=specific,
                                interpretation="Explicit negative statement; supports a NO determination if from a direct source.",
                                confidence=conf, negative_statement=True)

    if L.THIRD_PARTY_MODEL.search(sentence) and self_ref:
        nature, conf = "PARTNER_DEPENDENCY", 0.8
        cues.append("vendor's own statement that its services integrate third-party AI models")
    elif source_type == "official_job_posting":
        nature, conf = "HIRING_SIGNAL", 0.75
        cues.append("official job posting")
    elif L.COMMENTARY.search(sentence) and not (L.CONCRETE.search(sentence) and self_ref and not L.MODAL.search(sentence)):
        nature, conf = "INDUSTRY_COMMENTARY", 0.8
        cues.append(f"commentary/advocacy cue '{L.COMMENTARY.search(sentence).group(0)}'")
    elif partner_hits and not vendor_named:
        nature, conf = "PARTNER_DEPENDENCY", 0.75
        cues.append(f"describes AI in third-party platform the vendor implements ({', '.join(sorted(set(partner_hits)))})")
    elif not self_ref:
        nature, conf = "INDUSTRY_COMMENTARY", 0.7
        cues.append("no reference to the vendor or its own offering")
    elif L.WORKFORCE.search(sentence) and not L.CLIENT_PRODUCT.search(sentence.replace("platform", "")):
        nature, conf = "INTERNAL_OPERATIONAL_USE", 0.75
        cues.append(f"workforce/internal cue '{L.WORKFORCE.search(sentence).group(0)}'")
    elif L.MODAL.search(sentence) and not L.CONCRETE.search(sentence):
        nature, conf = "MARKETING_ONLY", 0.75
        cues.append(f"capability or aspirational language '{L.MODAL.search(sentence).group(0)}' without a concrete deployment statement")
    elif L.CONCRETE.search(sentence) and (L.CLIENT_PRODUCT.search(sentence) or rel >= 0.5):
        if specific and rel >= svc_min:
            nature, conf = "SERVICE_INTEGRATED", 0.85
            cues.append("concrete deployment statement naming the contracted service")
        else:
            nature, conf = "PRODUCT_FEATURE", 0.8
            cues.append(f"concrete deployment language '{L.CONCRETE.search(sentence).group(0)}' tied to products/clients")
    elif L.CONCRETE.search(sentence):
        nature, conf = "INTERNAL_OPERATIONAL_USE", 0.6
        cues.append("concrete use without client/product reference")
    else:
        nature, conf = "UNKNOWN", 0.5
        cues.append("AI mentioned without usage or capability cues")

    if official and self_ref:
        directness = "vendor_self_statement"
    elif self_ref:
        directness = "third_party_about_vendor"
    else:
        directness = "commentary"

    scope = ("names the contracted service" if specific else
             "no service-specific term — treated as vendor-level, not confirmed in the contracted service")
    interp = (f"Classified {nature}: {'; '.join(cues)}. Service relevance {rel:.2f}"
              f"{' (matched: ' + ', '.join(rel_terms) + ')' if rel_terms else ''}; {scope}.")
    if providers:
        interp += " Named provider(s): " + ", ".join(p.name for p in providers) + "."
    claim = _claim(ctx, nature, ai_types)
    return EvidenceProposal(exact_excerpt=sentence, claim=claim, nature=nature, ai_types=ai_types,
                            providers=providers, directness=directness, service_relevance=rel,
                            relevance_terms=rel_terms, service_specific=specific, interpretation=interp,
                            confidence=conf)


_CLAIMS = {
    "SERVICE_INTEGRATED": "{v} states AI is used within the contracted service{t}",
    "PRODUCT_FEATURE": "{v} states AI is deployed in its products or client services{t}",
    "INTERNAL_OPERATIONAL_USE": "{v} uses AI internally{t}",
    "PARTNER_DEPENDENCY": "{v} relies on or implements third-party AI platforms or models{t}",
    "MARKETING_ONLY": "{v} makes an AI capability or aspiration claim without a concrete deployment statement",
    "HIRING_SIGNAL": "{v} is hiring for AI/ML skills{t}",
    "INDUSTRY_COMMENTARY": "General AI commentary, not a statement of {v}'s own AI use",
    "UNKNOWN": "AI is mentioned in connection with {v}; nature unclear",
}


def _claim(ctx: VendorContext, nature: str, types: list[str]) -> str:
    short = ctx.aliases[-1] if ctx.aliases else ctx.name
    known = [t for t in types if t != "Unknown"]
    return _CLAIMS[nature].format(v=short, t=f" ({', '.join(known)})" if known else "")


def analyze_source(content: str, title: str, ctx: VendorContext, *, official: bool, source_type: str,
                   methodology) -> list[EvidenceProposal]:
    ac = methodology["ai_classification"]
    cap, svc_min = float(ac["adjacent_product_relevance_cap"]), float(ac["service_integrated_min_relevance"])
    proposals: list[EvidenceProposal] = []
    for m in re.finditer(r"[^\n]+", content):
        paragraph = m.group(0)
        if _is_heading(paragraph) or _same_text(paragraph, title):
            continue                     # titles/headings are context, not evidence
        units = sentences(paragraph)
        i = 0
        while i < len(units):
            off, sent = units[i]
            # very short sentences ("Bring your own LLM.") are joined with the next
            # one so the excerpt stays meaningful and remains a contiguous span
            while len(sent) < 40 and i + 1 < len(units):
                i += 1
                n_off, n_sent = units[i]
                sent = paragraph[off:n_off + len(n_sent)]
            i += 1
            if len(sent) < 20:
                continue
            p = classify_sentence(sent, paragraph, title or "", ctx, official=official, source_type=source_type,
                                  cap=cap, svc_min=svc_min)
            if p:
                proposals.append(p)
    return proposals


def _same_text(a: str, b: str | None) -> bool:
    if not b:
        return False
    norm = lambda x: re.sub(r"[^a-z0-9]", "", x.lower())
    return norm(a) and (norm(a) == norm(b) or norm(b).startswith(norm(a)))


def _is_heading(line: str) -> bool:
    t = line.strip()
    return len(t.split()) <= 14 and not re.search(r"[.!?:;\"”]$", t)
