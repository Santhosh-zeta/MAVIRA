"""Structured-output contract for evidence proposals (rule-based or LLM).
Every proposal, whatever produced it, is validated against this schema and then
against the source text before it can become evidence."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

Nature = Literal["SERVICE_INTEGRATED", "PRODUCT_FEATURE", "INTERNAL_OPERATIONAL_USE", "MARKETING_ONLY",
                 "HIRING_SIGNAL", "PARTNER_DEPENDENCY", "INDUSTRY_COMMENTARY", "UNKNOWN"]
AI_TYPES = ["Generative AI", "Machine Learning", "Predictive Analytics", "NLP", "Computer Vision",
            "Recommendation Systems", "AI-assisted Automation", "Agentic AI", "Fraud Detection", "Risk Scoring",
            "Document Intelligence", "Speech/Voice AI", "Other", "Unknown"]
Directness = Literal["vendor_self_statement", "third_party_about_vendor", "commentary"]


class ProposedProvider(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    type: str = Field(default="FOUNDATION_MODEL", max_length=48)
    matched: str | None = None


class EvidenceProposal(BaseModel):
    exact_excerpt: str = Field(min_length=20, max_length=1500)
    claim: str = Field(min_length=5, max_length=400)
    nature: Nature
    ai_types: list[str] = Field(default_factory=lambda: ["Unknown"])
    providers: list[ProposedProvider] = Field(default_factory=list)
    directness: Directness = "vendor_self_statement"
    service_relevance: float = Field(default=0.0, ge=0.0, le=1.0)
    relevance_terms: list[str] = Field(default_factory=list)
    service_specific: bool = False
    interpretation: str = Field(min_length=5, max_length=1500)
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    negative_statement: bool = False

    @field_validator("ai_types")
    @classmethod
    def _known_types(cls, v: list[str]) -> list[str]:
        cleaned = [t for t in v if t in AI_TYPES]
        return cleaned or ["Unknown"]


class LLMEvidenceResponse(BaseModel):
    proposals: list[EvidenceProposal] = Field(default_factory=list, max_length=25)
