"""Optional LLM-backed evidence proposer (via LiteLLM).

Only used when LLM_PROVIDER is set. The LLM proposes excerpts and classifies
them; it never scores strength or risk. Every proposal is schema-validated,
and then the exact excerpt must be found in the source text or it is rejected.
Providers proposed by the LLM are kept only if their name appears in the
excerpt. On any failure the rule-based analyzer is used and the failure logged.

DATA EGRESS: when enabled, the text of public vendor web pages and the vendor's
name/category/service description are sent to the configured provider. No
Meridian customer data is sent — the inventory has none beyond those fields.
"""
from __future__ import annotations

import json
import time

from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.schemas.llm import AI_TYPES, EvidenceProposal, LLMEvidenceResponse
from app.services.ai import rule_analyzer
from app.services.ai.lexicon import providers_in

log = get_logger(__name__)
PROMPT_VERSION = "mavira-evidence-v1"

_MODEL_PREFIX = {"openai": "openai/", "azure": "azure/", "anthropic": "anthropic/", "gemini": "gemini/",
                 "ollama": "ollama/"}

SYSTEM_PROMPT = f"""You are a third-party-risk analyst extracting evidence of AI usage by a vendor.
Return JSON: {{"proposals": [{{"exact_excerpt": str, "claim": str, "nature": str, "ai_types": [str],
"providers": [{{"name": str, "type": str}}], "directness": str, "service_relevance": float,
"interpretation": str, "confidence": float}}]}}.
Rules:
- exact_excerpt MUST be copied character-for-character from the SOURCE TEXT. Never paraphrase.
- One sentence (or two adjacent sentences) per proposal. Only sentences that mention AI/ML.
- nature is one of SERVICE_INTEGRATED, PRODUCT_FEATURE, INTERNAL_OPERATIONAL_USE, MARKETING_ONLY,
  HIRING_SIGNAL, PARTNER_DEPENDENCY, INDUSTRY_COMMENTARY, UNKNOWN.
  Aspirational or "can/will/could" claims without a concrete deployment are MARKETING_ONLY.
  General statements about the industry are INDUSTRY_COMMENTARY.
  SERVICE_INTEGRATED only if the excerpt ties AI to the specific contracted service named below.
- ai_types from: {", ".join(AI_TYPES)}.
- providers: only model/AI providers explicitly named in the excerpt as used by the vendor. Never infer.
- directness: vendor_self_statement | third_party_about_vendor | commentary.
- If nothing qualifies return {{"proposals": []}}."""


class LLMUnavailable(RuntimeError):
    pass


class LLMAnalyzer:
    def __init__(self, settings: Settings | None = None):
        self.s = settings or get_settings()
        if self.s.llm_provider.lower() == "none":
            raise LLMUnavailable("LLM disabled")
        try:
            import litellm  # noqa: F401
        except ImportError as exc:
            raise LLMUnavailable("litellm not installed (pip install -r requirements-llm.txt)") from exc
        if not self.s.llm_model:
            raise LLMUnavailable("LLM_MODEL not configured")
        self.model = _MODEL_PREFIX.get(self.s.llm_provider.lower(), "") + self.s.llm_model
        self.name = f"litellm:{self.model}"

    def propose(self, content: str, title: str, ctx: rule_analyzer.VendorContext, *, official: bool,
                source_type: str, methodology) -> tuple[list[EvidenceProposal], dict]:
        import litellm
        user = (f"VENDOR: {ctx.name}\nCATEGORY: {ctx.category}\nCONTRACTED SERVICE: {ctx.service}\n"
                f"SOURCE TYPE: {source_type} (official vendor source: {official})\nTITLE: {title}\n\n"
                f"SOURCE TEXT:\n{content[:12000]}")
        t0 = time.monotonic()
        meta = {"model": self.model, "prompt_version": PROMPT_VERSION}
        resp = litellm.completion(model=self.model, temperature=self.s.llm_temperature,
                                  api_base=self.s.llm_api_base, response_format={"type": "json_object"},
                                  messages=[{"role": "system", "content": SYSTEM_PROMPT},
                                            {"role": "user", "content": user}])
        meta["latency_ms"] = int((time.monotonic() - t0) * 1000)
        raw = resp.choices[0].message.content
        try:
            parsed = LLMEvidenceResponse.model_validate(json.loads(raw))
        except (json.JSONDecodeError, ValidationError) as exc:
            raise ValueError(f"invalid LLM output: {type(exc).__name__}") from exc
        out = []
        for p in parsed.proposals:
            # keep only providers actually named in the excerpt (no inference)
            named = {x["name"] for x in providers_in(p.exact_excerpt)}
            p.providers = [x for x in p.providers if any(x.name.split()[0].lower() in n.lower() for n in named)]
            rel, terms, specific = rule_analyzer.service_relevance(
                p.exact_excerpt, ctx, float(methodology["ai_classification"]["adjacent_product_relevance_cap"]))
            p.service_relevance, p.relevance_terms, p.service_specific = rel, terms, specific
            if p.nature == "SERVICE_INTEGRATED" and not specific:
                p.nature = "PRODUCT_FEATURE"      # deterministic guard
            out.append(p)
        return out, meta
