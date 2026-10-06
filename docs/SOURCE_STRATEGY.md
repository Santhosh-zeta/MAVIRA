# MAVIRA — Source Strategy and Evidentiary Weight

All numbers below come from `backend/app/config/methodology.yaml` (version 1.0.0) and change only through
a new methodology version.

## 1. Principle

We are not asking "does this company talk about AI?" but "is AI used in the service Meridian receives, and
can we show it?" Three consequences:

1. A statement only counts if it is about the vendor's **own** offering and describes a **concrete deployment**.
2. Every claim we export must be a **verbatim excerpt** that exists in a stored copy of the source.
3. Silence is not a "No". Absence of evidence is reported with the scope that was searched.

## 2. Source categories and reliability

| Level (weight) | Source types | Why |
|---|---|---|
| DIRECT (1.0) | Vendor product pages, technical/developer documentation, dedicated AI pages, trust centre / sub-processor lists / privacy pages, official job postings, regulatory filings (sec.gov), official executive statements on the vendor domain | Vendor is accountable for the content and it describes how the product works or what it is building |
| MEDIUM (0.75) | Vendor press releases and investor material, vendor insights/blog articles, partner announcements on the partner's own domain (e.g. openai.com, microsoft.com, Google Cloud press), executive social posts found by the executive-statement query | Official but promotional, or authored by a counterparty, or authorship not machine-verifiable |
| SUPPORTING (0.55) | Credible news (Reuters, WSJ, FT, Bloomberg, American Banker, PYMNTS, Fortune, Business Wire) | Independent but second-hand |
| LOW (0.25) | LinkedIn/Medium/Facebook/X content, directories and aggregators (Tracxn, AppsRunTheWorld, Birdeye, Crunchbase), anything unmatched | Unverified or derivative |

Classification is rule-ordered: vendor-domain path rules first (whole path tokens, so `api` does not match
`shaping`), then partner and news domains, then LOW. When a vendor URL matches only the generic page rule,
the search category that found it (insights, press, careers…) refines the type.

## 3. Evidence strength (per excerpt, 0–100)

| Component | Weight | Scoring |
|---|---|---|
| Source reliability | 0.30 | level weight above |
| Directness | 0.20 | vendor self-statement 1.0; third party about the vendor 0.7; general commentary 0.2 |
| Specificity | 0.20 | 0.25 base, +0.15 per named AI type (max 2), +0.2 named provider, +0.1 quantified, +0.1 named product/solution |
| Service relevance | 0.15 | keyword overlap with the vendor's category and its *Service / Business Process* text; +specific-term bonus when the excerpt names the contracted service (e.g. DNA, RTP); capped at 0.6 without such a term |
| Independence | 0.05 | 1.0 if the same AI type is evidenced on another domain, else 0.5 |
| Recency | 0.10 | ≤12 months 1.0, ≤24 0.7, ≤48 0.4, older 0.2, undated 0.5 |

Levels: VERY_STRONG ≥ 80, STRONG ≥ 65, MODERATE ≥ 45, WEAK < 45. The breakdown is stored and shown on every
evidence card.

**Classification confidence is separate.** It is how sure the classifier is about the *signal type*
(cue clarity), and, at vendor level, how sure we are about the YES / INCONCLUSIVE / NO determination.
A STRONG excerpt can still be a marketing claim; a MODERATE excerpt can be clearly a product capability.

## 4. Assessment depth by tier

| Tier | Depth | Source categories added | Max sources | Independent sources sought | Extras | Why this depth |
|---|---|---|---|---|---|---|
| Low | Baseline | official site, product pages, AI pages | 4 | 1 | — | Limited impact; confirm from the vendor's own product material only |
| Medium | Standard | + careers, engineering blog, developer docs, trust/security, partner pages | 8 | 1 | — | Hiring and engineering material reveal AI that marketing omits |
| High | Enhanced | + regulatory filings, investor disclosures, sub-processor lists, press releases, executive statements, insights | 14 | 2 | provider investigation, negative-evidence review | Model providers and AI risk factors are disclosed in filings, sub-processor lists and executive commentary |
| Critical | Full | + third-party/partner announcements, industry press | 24 | 2 | all of the above + mandatory analyst sign-off | Highest impact: corroborate across independent sources, search for named providers directly, record what was checked |

Each category has query templates (e.g. `site:{domain} subprocessors OR sub-processors`,
`"{name}" OpenAI OR "Azure OpenAI" OR Anthropic OR Gemini OR Bedrock`). Depth follows the tier, never the
volume of material a vendor publishes.

## 5. AI detection logic

1. **Candidate sentences** contain an AI term (artificial intelligence, AI, machine learning, ML, generative,
   GenAI, LLM, Copilot, ChatGPT, neural network, NLP, predictive analytics, anomaly detection, agentic,
   digital employees, foundation/frontier models, computer vision, speech recognition, chatbot, Model
   Context Protocol) or a named AI platform (Azure OpenAI, Foundry, Bedrock, Vertex AI, Gemini, watsonx…).
   "Intelligent" alone is not a trigger.
2. **Signal type** by ordered cues (all shown in the interpretation text):
   - vendor states services integrate third-party AI models → PARTNER_DEPENDENCY
   - official job posting → HIRING_SIGNAL
   - advocacy/commentary cues (urge, regulators, survey, "the industry", "has seen", predictions) without a
     concrete self-statement → INDUSTRY_COMMENTARY
   - describes AI in a third-party platform the vendor implements (from the vendor description, e.g.
     Automic) → PARTNER_DEPENDENCY
   - no reference to the vendor or first person on its own site → INDUSTRY_COMMENTARY
   - workforce/internal cues without client/product cues → INTERNAL_OPERATIONAL_USE
   - capability or aspirational language (can, will, could, potential, later) without a concrete deployment
     verb → MARKETING_ONLY
   - concrete deployment (already, in production, powers, deployed, processed, handles, in its own…) tied to
     clients/products or relevant to the service → PRODUCT_FEATURE, or SERVICE_INTEGRATED if the excerpt
     names the contracted service
3. **AI types** from a pattern lexicon (Agentic, Generative, Fraud Detection, Risk Scoring, Predictive
   Analytics, ML, NLP, AI-assisted Automation, Document Intelligence, Speech/Voice, Recommendation, Vision).
4. **Providers** are recorded only when named in a validated, non-commentary excerpt **with a usage
   relation** ("powered by NVIDIA", "including OpenAI frontier models", "tokens in Foundry"). "OpenAI … has
   spotlighted BNY" is a mention, not usage. Provider linkage is `SERVICE_LINKED` only when the excerpt also
   names the contracted service; otherwise `ENTERPRISE_LEVEL_ONLY`. If none: `NOT_PUBLICLY_DISCLOSED` —
   never "no provider".

Signal weights into AI exposure: SERVICE_INTEGRATED 1.0, PRODUCT_FEATURE 0.85, PARTNER_DEPENDENCY 0.6,
INTERNAL_OPERATIONAL_USE 0.5, HIRING_SIGNAL 0.35, UNKNOWN 0.2, MARKETING_ONLY 0.1, INDUSTRY_COMMENTARY 0.

## 6. Determination rules

- **YES**: one SERVICE_INTEGRATED/PRODUCT_FEATURE excerpt ≥ 65, or two from distinct sources ≥ 45.
- **NO**: explicit negative statement ("does not use artificial intelligence") from a DIRECT source and no
  contrary signal.
- **INCONCLUSIVE**: otherwise.

Vendor-level evidence strength shown in the register is the strongest confirming excerpt, else the
strongest substantive (partner/internal) signal; marketing and hiring signals do not set it.

## 7. Negative-evidence handling

When no weighted signal is found, the assessment records `sources_checked`, `searches_performed`,
`assessment_scope` (tier categories), the list of sources without AI content, and the statement
**"NO MEANINGFUL PUBLIC EVIDENCE IDENTIFIED WITHIN ASSESSED OSINT SCOPE"**. The risk class becomes *None
identified* with an explicit caveat, and for High/Critical vendors a questionnaire recommendation is emitted.
Vendor home pages with no AI content are deliberately kept as sources: they are part of what was checked.

## 8. Confidence

- Excerpt classification confidence: 0.5–0.85 depending on cue clarity (e.g. 0.85 for a concrete statement
  naming the service, 0.6 for concrete use with no client reference).
- YES confidence: 0.45 + 0.4 × best strength + 0.06 per extra supporting source + 0.04 if a DIRECT source
  supports it + 0.05 if service-specific, capped at 0.97.
- INCONCLUSIVE confidence: 0.55 + 0.04 per search (max 6) + 0.02 per source (max 5), minus 0.1 when ambiguous
  signals exist, capped at 0.85.

## 9. Source traceability

Every exported claim carries: exact excerpt, URL, source type, reliability, collection method (LIVE /
CACHED / DEMO_MOCK), retrieval date, published date where known, content hash of the stored text, character
offsets of the excerpt, proposing analyzer and strength breakdown. The UI opens the stored text with the
excerpt highlighted. Rejected proposals are kept with the reason.

## 10. Risk scoring (summary)

AI presence = min(1, exposure / 0.6) × 0.8 if no excerpt ties AI to the contracted service. Category base
values: data sensitivity, operational dependency, regulatory exposure (from criticality); provider
uncertainty 1.0 / 0.6 / 0.3 and transparency 1.0 / 0.5 / 0.2 (not disclosed / enterprise level / service
linked); retention and training 0.8 when undisclosed; contractual 0.7 (contract terms not in input);
decision impact by AI type (agentic 1.0, fraud/risk 0.9, automation 0.8 …). Weights: data exposure 0.16,
decision impact 0.14, operational dependency 0.14, regulatory 0.12, sub-processor 0.10, contractual 0.10,
transparency 0.08, retention 0.08, training 0.08. Classes: Critical ≥ 75, High ≥ 50, Medium ≥ 25, Low > 0,
None identified = no AI signal. Floor: confirmed AI in a Critical vendor without a service-linked provider
is at least High.
