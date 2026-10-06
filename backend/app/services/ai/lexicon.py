"""Controlled vocabularies for AI-signal detection. Kept in one module so the
detection logic is inspectable and testable in isolation."""
from __future__ import annotations

import re

# Terms that make a sentence an AI candidate. "intelligent" on its own is
# deliberately NOT a trigger (e.g. "intelligent mail inserters").
AI_TERMS = [
    re.compile(r"\bAI\b"),
    re.compile(r"\bA\.I\.\B"),
    re.compile(r"artificial intelligence", re.I),
    re.compile(r"machine[- ]learning", re.I),
    re.compile(r"\bML\b"),
    re.compile(r"\bgenerative\b", re.I),
    re.compile(r"\bGenAI\b", re.I),
    re.compile(r"\bLLMs?\b"),
    re.compile(r"large language models?", re.I),
    re.compile(r"\bCopilot\b"),
    re.compile(r"\bChatGPT\b"),
    re.compile(r"neural networks?", re.I),
    re.compile(r"deep learning", re.I),
    re.compile(r"\bNLP\b"),
    re.compile(r"natural[- ]language (processing|understanding|workflow|interface|queries)", re.I),
    re.compile(r"predictive analytics", re.I),
    re.compile(r"anomaly detection", re.I),
    re.compile(r"\bagentic\b", re.I),
    re.compile(r"digital employees", re.I),
    re.compile(r"(foundation|frontier) models?", re.I),
    re.compile(r"computer vision", re.I),
    re.compile(r"speech recognition|voice biometrics|call transcription", re.I),
    re.compile(r"\bchatbots?\b", re.I),
    re.compile(r"Model Context Protocol"),
]


def has_ai_term(text: str) -> bool:
    return any(p.search(text) for p in AI_TERMS) or any(p["regex"].search(text) for p in PROVIDERS
                                                         if p["type"] != "COMPUTE_INFRASTRUCTURE")


def ai_terms_in(text: str) -> list[str]:
    found = []
    for p in AI_TERMS:
        m = p.search(text)
        if m:
            found.append(m.group(0))
    return found


AI_TYPE_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("Agentic AI", re.compile(r"\bagentic\b|\bAI agents?\b|digital employees|\bagents?\b.*\b(build|handle|autonomous)|without human handoff", re.I)),
    ("Generative AI", re.compile(r"generative|\bGenAI\b|\bLLMs?\b|large language|Copilot|ChatGPT|frontier models?|foundation models?|generates scripts|tokens", re.I)),
    ("Fraud Detection", re.compile(r"fraud (detection|prevention)|anomaly detection|detect(ion)? .*fraud", re.I)),
    ("Risk Scoring", re.compile(r"risk (management|scoring|signals|insights)|credit decision", re.I)),
    ("Predictive Analytics", re.compile(r"predictive analytics|predict(s|ing)? (potential|customer|behaviou?r|failures)|forecast", re.I)),
    ("Machine Learning", re.compile(r"machine[- ]learning|\bML\b", re.I)),
    ("NLP", re.compile(r"natural[- ]language|\bNLP\b|plain English", re.I)),
    ("AI-assisted Automation", re.compile(r"automat|troubleshoot|root[- ]cause|workflow building", re.I)),
    ("Document Intelligence", re.compile(r"document (intelligence|understanding|extraction)|\bOCR\b|contract review", re.I)),
    ("Speech/Voice AI", re.compile(r"speech|voice|transcri", re.I)),
    ("Recommendation Systems", re.compile(r"recommendation engine|personali[sz]ed (engagement|offers)", re.I)),
    ("Computer Vision", re.compile(r"computer vision|image recognition", re.I)),
]


def ai_types_in(text: str) -> list[str]:
    types = [name for name, pat in AI_TYPE_PATTERNS if pat.search(text)]
    return types or ["Unknown"]


# Named providers. A provider is only recorded when a usage relation appears in
# the same validated excerpt — a mere mention does not count.
PROVIDERS: list[dict] = [
    {"name": "Microsoft (Azure OpenAI / Foundry / Copilot)", "type": "MODEL_PLATFORM",
     "pattern": r"Azure OpenAI|Microsoft Foundry|Azure AI Foundry|\bFoundry\b|Microsoft 365 Copilot|GitHub Copilot|Azure-powered AI"},
    {"name": "OpenAI", "type": "FOUNDATION_MODEL", "pattern": r"\bOpenAI\b(?!,? the company)|\bChatGPT Enterprise\b|\bGPT-\d"},
    {"name": "Google (Gemini / Vertex AI)", "type": "FOUNDATION_MODEL", "pattern": r"\bGemini\b|Vertex AI"},
    {"name": "Anthropic (Claude)", "type": "FOUNDATION_MODEL", "pattern": r"\bAnthropic\b|\bClaude\b"},
    {"name": "AWS (Bedrock)", "type": "MODEL_PLATFORM", "pattern": r"Amazon Bedrock|AWS Bedrock|\bBedrock\b"},
    {"name": "NVIDIA", "type": "COMPUTE_INFRASTRUCTURE", "pattern": r"\bNVIDIA\b"},
    {"name": "Meta (Llama)", "type": "FOUNDATION_MODEL", "pattern": r"\bLlama\b|Meta AI"},
    {"name": "Mistral", "type": "FOUNDATION_MODEL", "pattern": r"\bMistral\b"},
    {"name": "Cohere", "type": "FOUNDATION_MODEL", "pattern": r"\bCohere\b"},
    {"name": "IBM watsonx", "type": "MODEL_PLATFORM", "pattern": r"watsonx|IBM Watson"},
    {"name": "Databricks", "type": "MODEL_PLATFORM", "pattern": r"\bDatabricks\b|Mosaic AI"},
    {"name": "Snowflake (Cortex)", "type": "MODEL_PLATFORM", "pattern": r"Snowflake Cortex|\bCortex AI\b"},
]
for p in PROVIDERS:
    p["regex"] = re.compile(p["pattern"])

PROVIDER_USAGE_CUE = re.compile(
    r"powered by|built on|built with|\bwith\b|\busing\b|\buses\b|use of|\bdeploy|\bin\b|including|leverag|"
    r"partner|collaborat|integrat|models?\b|platform|Enterprise\b|tokens", re.I)


def providers_in(text: str) -> list[dict]:
    found = []
    for p in PROVIDERS:
        m = p["regex"].search(text)
        if m and PROVIDER_USAGE_CUE.search(text):
            found.append({"name": p["name"], "type": p["type"], "matched": m.group(0)})
    return found


# Linguistic cues used by the rule-based classifier ---------------------------------
FIRST_PERSON = re.compile(r"\b(we|our|us|we’re|we're|we've|we’ve)\b", re.I)
MODAL = re.compile(r"\b(will|can|could|may|might|believe|potential|future|later|predicts?|expect(ed|s)?|"
                   r"aim|plan(s|ned)?|aspire|envision|poised|transform)\b", re.I)
CONCRETE = re.compile(r"\b(already|in production|has been \w+ing|existing use|deployment|powers|powered|deployed|deploy(s|ing)?|processed|"
                      r"uses|used|handle[sd]?|built on|runs|live|operat(es|ing)|delivers?|launched|introduced|"
                      r"embedded|integrated|in its own)\b", re.I)
WORKFORCE = re.compile(r"(?<!digital )\b(employees|workforce|engineers|staff|developer productivity|across the organization|"
                       r"internal|productivity|colleagues)\b", re.I)
CLIENT_PRODUCT = re.compile(r"\b(clients?|customers?|financial institutions|merchants|products?|solutions?|"
                            r"service[s]?|servicing)\b", re.I)
COMMENTARY = re.compile(r"\b(urge[sd]?|regulators?|regulatory proposal|survey|the industry|organizations need|"
                        r"has seen|writing is on the wall|predicts|in the quest|future of|grown smarter|"
                        r"whether or not the firm|every industry|criminals|fraudsters)\b", re.I)
NEGATIVE_USE = re.compile(r"\b(does not|do not|doesn't|don't|never) use (any )?(ai|artificial intelligence|machine learning)\b", re.I)
THIRD_PARTY_MODEL = re.compile(r"third[- ]party (artificial intelligence|AI) models?|third[- ]party (LLM|model) providers?", re.I)
