"""Generate the MAVIRA Optiv Case Study 1 presentation deck."""
from __future__ import annotations

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt
import pptx.util as util

# ── Colour palette ─────────────────────────────────────────────────────────────
NAVY   = RGBColor(0x0A, 0x1F, 0x44)   # deep navy – headers / backgrounds
TEAL   = RGBColor(0x00, 0x7A, 0x87)   # Optiv teal – accents
GOLD   = RGBColor(0xE5, 0xA8, 0x23)   # amber – callouts / critical
WHITE  = RGBColor(0xFF, 0xFF, 0xFF)
LGREY  = RGBColor(0xF2, 0xF2, 0xF2)   # slide background
DGREY  = RGBColor(0x44, 0x44, 0x44)   # body text
RED    = RGBColor(0xC0, 0x39, 0x2B)   # risk CRITICAL
ORANGE = RGBColor(0xE6, 0x7E, 0x22)   # risk HIGH
AMBER  = RGBColor(0xF3, 0x9C, 0x12)   # risk MEDIUM
GREEN  = RGBColor(0x27, 0xAE, 0x60)   # risk LOW / positive

SLIDE_W = Inches(13.33)
SLIDE_H = Inches(7.5)


# ── Helpers ────────────────────────────────────────────────────────────────────
def prs_new() -> Presentation:
    prs = Presentation()
    prs.slide_width  = SLIDE_W
    prs.slide_height = SLIDE_H
    return prs


def blank(prs: Presentation):
    blank_layout = prs.slide_layouts[6]  # completely blank
    return prs.slides.add_slide(blank_layout)


def rect(slide, left, top, width, height, fill=None, line=None):
    shape = slide.shapes.add_shape(
        1,  # MSO_SHAPE_TYPE.RECTANGLE
        Inches(left), Inches(top), Inches(width), Inches(height))
    shape.line.fill.background() if line is None else None
    if fill:
        shape.fill.solid()
        shape.fill.fore_color.rgb = fill
    else:
        shape.fill.background()
    if line is None:
        shape.line.fill.background()
    return shape


def txbox(slide, left, top, width, height, text, size=14, bold=False, color=DGREY,
          align=PP_ALIGN.LEFT, wrap=True):
    tb = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = tb.text_frame
    tf.word_wrap = wrap
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    return tb


def heading_bar(slide, title: str, subtitle: str = ""):
    """Navy bar across the top of content slides."""
    rect(slide, 0, 0, 13.33, 1.1, fill=NAVY)
    txbox(slide, 0.3, 0.12, 10, 0.5, title, size=24, bold=True, color=WHITE)
    if subtitle:
        txbox(slide, 0.3, 0.65, 10, 0.38, subtitle, size=13, color=RGBColor(0xBB, 0xD5, 0xE8))
    # teal accent line
    rect(slide, 0, 1.1, 13.33, 0.04, fill=TEAL)


def footer(slide, page: str):
    rect(slide, 0, 7.15, 13.33, 0.35, fill=NAVY)
    txbox(slide, 0.2, 7.17, 8, 0.28, "MAVIRA · Meridian AI Vendor Intelligence & Risk Assessment · CONFIDENTIAL",
          size=8, color=RGBColor(0x99, 0xBB, 0xCC))
    txbox(slide, 11.5, 7.17, 1.6, 0.28, page, size=8, color=RGBColor(0x99, 0xBB, 0xCC), align=PP_ALIGN.RIGHT)


def bullet_list(slide, left, top, width, height, items: list[tuple[str, int]]):
    """items = [(text, indent_level), ...]"""
    tb = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = tb.text_frame
    tf.word_wrap = True
    first = True
    for text, level in items:
        if first:
            p = tf.paragraphs[0]
            first = False
        else:
            p = tf.add_paragraph()
        p.level = level
        p.space_before = Pt(3 if level == 0 else 1)
        run = p.add_run()
        run.text = ("• " if level == 0 else "  ◦ ") + text
        run.font.size = Pt(13 if level == 0 else 11)
        run.font.color.rgb = DGREY if level == 0 else RGBColor(0x55, 0x55, 0x55)


def risk_badge(slide, left, top, label, color):
    r = rect(slide, left, top, 1.4, 0.38, fill=color)
    txbox(slide, left + 0.05, top + 0.04, 1.3, 0.3, label, size=11, bold=True, color=WHITE,
          align=PP_ALIGN.CENTER)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 1 — Title
# ══════════════════════════════════════════════════════════════════════════════
def slide_title(prs):
    sl = blank(prs)
    # Full-bleed navy background
    rect(sl, 0, 0, 13.33, 7.5, fill=NAVY)
    # Teal diagonal accent (simulated with two rectangles)
    rect(sl, 0, 5.5, 13.33, 2.0, fill=RGBColor(0x00, 0x55, 0x66))
    rect(sl, 0, 6.5, 13.33, 1.0, fill=TEAL)

    txbox(sl, 0.8, 0.6, 11.5, 0.7, "OPTIV SECURITY · VIT INTERNSHIP RECRUITMENT 2026",
          size=13, color=GOLD, align=PP_ALIGN.CENTER)
    txbox(sl, 0.8, 1.4, 11.5, 1.2, "MAVIRA", size=52, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    txbox(sl, 0.8, 2.55, 11.5, 0.6,
          "Meridian AI Vendor Intelligence & Risk Assessment",
          size=20, color=RGBColor(0xBB, 0xD5, 0xE8), align=PP_ALIGN.CENTER)
    txbox(sl, 0.8, 3.3, 11.5, 0.5,
          "Case Study 1 — Vendor AI Usage Analysis",
          size=16, color=GOLD, align=PP_ALIGN.CENTER)
    txbox(sl, 0.8, 4.0, 11.5, 0.45,
          "Meridian Financial · Third-Party Risk Team",
          size=13, color=RGBColor(0x88, 0xAA, 0xBB), align=PP_ALIGN.CENTER)
    txbox(sl, 0.8, 5.7, 11.5, 0.4,
          "Team MAVIRA  ·  Presented October 2026",
          size=12, color=WHITE, align=PP_ALIGN.CENTER)
    txbox(sl, 0.8, 6.2, 11.5, 0.4,
          "CONFIDENTIAL — NOT FOR DISTRIBUTION",
          size=10, color=GOLD, align=PP_ALIGN.CENTER)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 2 — Problem & Mandate
# ══════════════════════════════════════════════════════════════════════════════
def slide_problem(prs):
    sl = blank(prs)
    rect(sl, 0, 0, 13.33, 7.5, fill=LGREY)
    heading_bar(sl, "The Problem", "Why this assessment exists")
    footer(sl, "2 / 14")

    # Left panel — problem statement
    rect(sl, 0.3, 1.3, 5.8, 5.6, fill=WHITE)
    txbox(sl, 0.5, 1.4, 5.4, 0.45, "Meridian Financial's Mandate", size=14, bold=True, color=NAVY)
    bullet_list(sl, 0.5, 1.9, 5.5, 4.8, [
        ("6 vendors process Meridian customer data and transactions", 0),
        ("Vendor AI usage is NOT captured in current contracts", 0),
        ("Regulators (OCC, Fed, CFPB) are examining AI third-party risk", 0),
        ("Risk of undetected model training on client data, autonomous decisions in payments, or undisclosed sub-processors", 0),
        ("Marketing language inflated vs. real AI deployment — cannot trust self-reported answers alone", 0),
    ])

    # Right panel — our answer
    rect(sl, 6.4, 1.3, 6.6, 5.6, fill=WHITE)
    txbox(sl, 6.6, 1.4, 6.2, 0.45, "MAVIRA's Answer", size=14, bold=True, color=TEAL)
    bullet_list(sl, 6.6, 1.9, 6.1, 4.8, [
        ("Deterministic 5-factor criticality scoring for every vendor", 0),
        ("Structured OSINT: source classification, strength scoring, exact-excerpt validation", 0),
        ("Reproducible AI classification: YES / NO / INCONCLUSIVE with evidence chain", 0),
        ("9-category AI security risk score (0-100) with transparent rationale", 0),
        ("Standards-grounded recommendations: NIST AI RMF, FFIEC SR 11-7, OCC 2023-17", 0),
        ("Full offline audit trail — SHA-256 hashed snapshots, no invented quotes", 0),
        ("Output: Excel workbook (findings) + this presentation (walkthrough)", 0),
    ])


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 3 — How MAVIRA Works (functional flow)
# ══════════════════════════════════════════════════════════════════════════════
def slide_how_mavira_works(prs):
    sl = blank(prs)
    rect(sl, 0, 0, 13.33, 7.5, fill=LGREY)
    heading_bar(sl, "How MAVIRA Works", "Fully deterministic — no hallucinated evidence, no AI scores scores")
    footer(sl, "3 / 14")

    stages = [
        ("1\nVendor\nInventory", NAVY, "6 vendors loaded from\nthe Excel workbook"),
        ("2\nCriticality\nEngine", TEAL, "5-factor weighted score\nOD·DS·PF·RE·DV"),
        ("3\nOSINT\nCollection", RGBColor(0x2E, 0x86, 0xAB), "Depth-gated search\nCACHED or LIVE mode"),
        ("4\nEvidence\nExtraction", RGBColor(0x5C, 0x4F, 0x8A), "Rule-based + optional\nLLM proposals"),
        ("5\nExact-Excerpt\nValidation", RGBColor(0x8A, 0x4F, 0x5C), "Every quote verified\nagainst source text"),
        ("6\nAI Usage\nDetermination", RGBColor(0xC0, 0x39, 0x2B), "YES / NO /\nINCONCLUSIVE"),
        ("7\nRisk\nScoring", ORANGE, "9 categories × AI\npresence index"),
        ("8\nRecommend-\nations", GREEN, "Rules-driven, standards-\ngrounded actions"),
    ]

    box_w = 1.5
    gap = 0.05
    total = len(stages) * box_w + (len(stages) - 1) * gap
    start_x = (13.33 - total) / 2

    for i, (label, color, desc) in enumerate(stages):
        x = start_x + i * (box_w + gap)
        rect(sl, x, 1.5, box_w, 1.4, fill=color)
        txbox(sl, x + 0.05, 1.55, box_w - 0.1, 1.3, label, size=10.5, bold=True, color=WHITE,
              align=PP_ALIGN.CENTER)
        if i < len(stages) - 1:
            txbox(sl, x + box_w, 2.05, gap + 0.25, 0.4, "→", size=16, bold=True, color=NAVY)
        txbox(sl, x, 3.05, box_w, 0.8, desc, size=9, color=DGREY, align=PP_ALIGN.CENTER)

    # Key design principles
    rect(sl, 0.3, 4.1, 12.7, 2.95, fill=WHITE)
    txbox(sl, 0.5, 4.2, 12.3, 0.4, "Key Design Principles", size=13, bold=True, color=NAVY)
    principles = [
        ("Methodology YAML", "All weights, rules and thresholds in one auditable config file — version-stamped per run"),
        ("Exact-Excerpt Only", "Every evidence record quotes verbatim text verified against the source; rejected if not found"),
        ("Evidence Strength 0-100", "Source reliability × directness × specificity × service relevance × recency × independence"),
        ("No AI in scoring", "LLM is optional evidence-proposal helper only; all scores are deterministic Python functions"),
        ("DEMO / LIVE modes", "DEMO uses SHA-256-hashed OSINT snapshots (fully offline); LIVE uses search API + SSRF-guarded fetcher"),
        ("Audit Trail", "Every run persists stage logs, rejection reasons, strength breakdowns, and risk factor rationales in SQLite/Postgres"),
    ]
    col_w = 6.0
    for i, (title, body) in enumerate(principles):
        col = i % 2
        row = i // 2
        x = 0.5 + col * col_w
        y = 4.7 + row * 0.72
        txbox(sl, x, y, col_w - 0.2, 0.25, f"▪ {title}: ", size=10.5, bold=True, color=TEAL)
        txbox(sl, x + 1.4, y, col_w - 1.6, 0.45, body, size=10, color=DGREY)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 4 — Architecture
# ══════════════════════════════════════════════════════════════════════════════
def slide_architecture(prs):
    sl = blank(prs)
    rect(sl, 0, 0, 13.33, 7.5, fill=LGREY)
    heading_bar(sl, "System Architecture", "Local-first · Docker Compose · Privacy-by-design")
    footer(sl, "4 / 14")

    # Three-column layout: Backend | Database | Frontend
    cols = [
        ("Backend (FastAPI)", NAVY, [
            "Python 3.12 · FastAPI",
            "Criticality engine (deterministic)",
            "Evidence strength scorer",
            "AI usage classifier",
            "Risk engine (9 categories)",
            "Recommendation engine",
            "SSRF-safe OSINT fetcher",
            "PDF extraction (pypdf)",
            "Playwright SPA fallback",
            "Excel workbook export",
            "Optional LLM analyzer",
        ]),
        ("Data Layer", TEAL, [
            "PostgreSQL (primary)",
            "SQLite (offline / test)",
            "Redis + RQ (async jobs)",
            "Methodology versions stored",
            "Full audit log per run",
            "Evidence chain persisted",
            "SHA-256 source hashes",
            "OSINT snapshot cache",
            "SQLAlchemy ORM",
        ]),
        ("Frontend (Next.js)", RGBColor(0x2E, 0x86, 0xAB), [
            "Next.js 16 · React 19 · TS",
            "Real-time run progress",
            "Vendor evidence explorer",
            "Risk radar chart",
            "Methodology editor",
            "Analyst override panel",
            "Excel import/export",
            "RBAC (admin / analyst / reviewer)",
            "Tailwind CSS · shadcn/ui",
        ]),
    ]
    col_w = 3.8
    for i, (title, color, items) in enumerate(cols):
        x = 0.3 + i * (col_w + 0.3)
        rect(sl, x, 1.25, col_w, 0.5, fill=color)
        txbox(sl, x + 0.1, 1.3, col_w - 0.2, 0.4, title, size=13, bold=True, color=WHITE)
        rect(sl, x, 1.75, col_w, 5.1, fill=WHITE)
        bullet_list(sl, x + 0.15, 1.85, col_w - 0.3, 4.9,
                    [(item, 0) for item in items])

    # Security callout
    rect(sl, 0.3, 6.9, 12.7, 0.45, fill=RGBColor(0xF0, 0xF8, 0xFF))
    txbox(sl, 0.5, 6.93, 12.3, 0.35,
          "Security: SSRF protection (scheme/port allowlist, DNS validation, private IP block, redirect re-check) · RBAC · "
          "Rate-limiting · PDF safe-parse · LLM prompt injection guard · SEC EDGAR-compliant User-Agent",
          size=9, color=NAVY)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 5 — OSINT Source Strategy
# ══════════════════════════════════════════════════════════════════════════════
def slide_source_strategy(prs):
    sl = blank(prs)
    rect(sl, 0, 0, 13.33, 7.5, fill=LGREY)
    heading_bar(sl, "OSINT Source Strategy", "Depth-gated collection · source classification · evidence strength scoring")
    footer(sl, "5 / 14")

    # Depth tiers table
    rect(sl, 0.3, 1.25, 12.7, 0.4, fill=NAVY)
    for col_i, (txt, w) in enumerate(zip(
            ["Tier", "Label", "Source Categories", "Max Sources", "Human Review"],
            [1.0, 1.5, 7.0, 1.6, 1.6])):
        x = 0.3 + sum([1.0, 1.5, 7.0, 1.6, 1.6][:col_i])
        txbox(sl, x + 0.05, 1.28, w - 0.1, 0.34, txt, size=10, bold=True, color=WHITE)

    tiers = [
        ("LOW",      "Baseline", "Official website, product pages, AI documentation", "4",  "No"),
        ("MEDIUM",   "Standard", "Baseline + careers, engineering blog, developer docs, trust/security, partner pages", "8",  "No"),
        ("HIGH",     "Enhanced", "Standard + regulatory filings, investor disclosures, sub-processors, press releases, exec statements", "14", "No"),
        ("CRITICAL", "Full",     "Enhanced + third-party partner, industry press · provider investigation · negative-evidence review", "24", "Yes"),
    ]
    tier_colors = {"LOW": GREEN, "MEDIUM": AMBER, "HIGH": ORANGE, "CRITICAL": RED}
    for row_i, (tier, label, cats, mx, hr) in enumerate(tiers):
        y = 1.65 + row_i * 0.55
        bg = LGREY if row_i % 2 == 0 else WHITE
        rect(sl, 0.3, y, 12.7, 0.55, fill=bg)
        rect(sl, 0.3, y + 0.08, 1.0, 0.38, fill=tier_colors[tier])
        txbox(sl, 0.32, y + 0.1, 0.96, 0.34, tier, size=10, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
        txbox(sl, 1.3, y + 0.08, 1.5, 0.38, label, size=10, color=DGREY)
        txbox(sl, 2.8, y + 0.08, 7.0, 0.4, cats, size=9.5, color=DGREY)
        txbox(sl, 9.8, y + 0.08, 1.6, 0.38, mx, size=10, color=DGREY, align=PP_ALIGN.CENTER)
        txbox(sl, 11.4, y + 0.08, 1.6, 0.38, hr, size=10, bold=(hr == "Yes"),
              color=RED if hr == "Yes" else GREEN, align=PP_ALIGN.CENTER)

    # Source reliability callout
    rect(sl, 0.3, 4.0, 12.7, 2.9, fill=WHITE)
    txbox(sl, 0.5, 4.1, 5.0, 0.4, "Evidence Strength Components (0-100)", size=12, bold=True, color=NAVY)
    txbox(sl, 6.0, 4.1, 6.6, 0.4, "Source Reliability Levels", size=12, bold=True, color=NAVY)

    strength_items = [
        "Source Reliability (30%) — DIRECT=1.0 · MEDIUM=0.75 · SUPPORTING=0.55 · LOW=0.25",
        "Directness (20%) — vendor self-statement vs. third-party vs. commentary",
        "Specificity (20%) — exact AI technology named, not generic claims",
        "Service Relevance (15%) — tied to the contracted service, not generic product",
        "Independence (5%) — corroborated across multiple domains",
        "Recency (10%) — published date: ≤12mo=1.0 · ≤24mo=0.7 · ≤48mo=0.4 · older=0.2",
    ]
    for i, item in enumerate(strength_items):
        txbox(sl, 0.5, 4.55 + i * 0.38, 5.3, 0.35, f"• {item}", size=9.5, color=DGREY)

    levels = [
        ("DIRECT", WHITE, NAVY, "Vendor's own domain · SEC EDGAR · official trust page"),
        ("MEDIUM", WHITE, TEAL, "Official press releases · investor disclosures · partner announcements"),
        ("SUPPORTING", WHITE, ORANGE, "Reuters · WSJ · Bloomberg · American Banker"),
        ("LOW", WHITE, RED, "LinkedIn · Medium · aggregators — never sole basis for YES"),
    ]
    for i, (lbl, fc, bc, desc) in enumerate(levels):
        y = 4.55 + i * 0.55
        rect(sl, 6.0, y, 1.5, 0.45, fill=bc)
        txbox(sl, 6.05, y + 0.06, 1.4, 0.33, lbl, size=10, bold=True, color=fc, align=PP_ALIGN.CENTER)
        txbox(sl, 7.6, y + 0.05, 5.3, 0.4, desc, size=9.5, color=DGREY)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 6 — Criticality Model (with V-000 validation)
# ══════════════════════════════════════════════════════════════════════════════
def slide_criticality(prs):
    sl = blank(prs)
    rect(sl, 0, 0, 13.33, 7.5, fill=LGREY)
    heading_bar(sl, "5-Factor Criticality Model", "Deterministic weighted score — validated against V-000 Larkspur worked example")
    footer(sl, "6 / 14")

    # Formula
    rect(sl, 0.3, 1.25, 12.7, 0.65, fill=NAVY)
    txbox(sl, 0.5, 1.3, 12.3, 0.55,
          "Score = OD(0.30) + DS(0.25) + PF(0.15) + RE(0.15) + DV(0.15)    "
          "│  CRITICAL ≥ 0.75  │  HIGH ≥ 0.55  │  MEDIUM ≥ 0.35  │  LOW ≥ 0.0",
          size=13, bold=True, color=WHITE, align=PP_ALIGN.CENTER)

    factors = [
        ("OD", "Operational\nDependency", "0.30", NAVY,
         "Total / Critical = 1.0\nHigh = 0.75\nModerate = 0.50\nLow = 0.25",
         "How badly would Meridian be hurt if this vendor stopped working tomorrow?"),
        ("DS", "Data\nSensitivity", "0.25", TEAL,
         "PAN / cardholder = 1.0\nTax ID / SSN = 1.0\nFull customer records = 1.0\nAccount PII = 0.9\nPrivileged access = 0.75",
         "What customer data does the vendor process? Highest-rule wins."),
        ("PF", "Payment\nFlow", "0.15", RGBColor(0x2E, 0x86, 0xAB),
         "Clearing / settlement / RTP / ACH = 1.0\nCore account processing = 0.9\nBatch / billing = 0.4",
         "Does the vendor touch money-in-motion?"),
        ("RE", "Regulatory\nExposure", "0.15", RGBColor(0x5C, 0x4F, 0x8A),
         "AML / KYC / BSA = 1.0\nCore banking records = 1.0\nConsumer lending = 0.9\nPayment system (NACHA) = 0.9\nOCC / FFIEC supervision = 0.8",
         "What regulatory frameworks govern this vendor relationship?"),
        ("DV", "Data\nVolume", "0.15", RED,
         "Log-scaled 1K → 100M records\nEntire customer base = 1.0\nPopulation named in data class = score\nN/A or unknown = 0.0",
         "How many customer records are in scope?"),
    ]

    box_w = 2.4
    for i, (abbr, name, wt, color, scale, meaning) in enumerate(factors):
        x = 0.3 + i * (box_w + 0.1)
        rect(sl, x, 2.0, box_w, 0.55, fill=color)
        txbox(sl, x + 0.05, 2.04, box_w - 0.1, 0.48,
              f"{abbr}  ·  weight {wt}",
              size=12, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
        rect(sl, x, 2.55, box_w, 1.1, fill=WHITE)
        txbox(sl, x + 0.08, 2.58, box_w - 0.16, 1.05, name + "\n" + scale, size=9, color=DGREY)
        rect(sl, x, 3.65, box_w, 0.65, fill=LGREY)
        txbox(sl, x + 0.08, 3.68, box_w - 0.16, 0.6, meaning, size=8.5, color=DGREY)

    # V-000 validation section
    rect(sl, 0.3, 4.4, 12.7, 0.4, fill=GOLD)
    txbox(sl, 0.5, 4.43, 12.3, 0.33,
          "V-000 Larkspur Worked Example — Validation (never modified by MAVIRA)",
          size=12, bold=True, color=NAVY, align=PP_ALIGN.CENTER)

    rect(sl, 0.3, 4.8, 12.7, 1.6, fill=WHITE)
    v000_rows = [
        ("OD: Critical (1.0) × 0.30 = 0.300", "DS: Full customer records (1.0) × 0.25 = 0.250",
         "PF: Core processing (0.9) × 0.15 = 0.135"),
        ("RE: Core banking records (1.0) × 0.15 = 0.150", "DV: 125,000 records, log-scaled ≈ 0.47 × 0.15 = 0.070",
         "Score: 0.905 → CRITICAL  ✓  matches provided answer"),
    ]
    for row_i, row in enumerate(v000_rows):
        for col_i, cell in enumerate(row):
            color = GREEN if "✓" in cell else DGREY
            txbox(sl, 0.5 + col_i * 4.2, 4.88 + row_i * 0.72, 4.1, 0.65, f"• {cell}",
                  size=10.5, color=color, bold=("✓" in cell))

    # Escalation rules callout
    rect(sl, 0.3, 6.5, 12.7, 0.82, fill=RGBColor(0xFF, 0xF0, 0xE0))
    txbox(sl, 0.5, 6.53, 12.3, 0.35, "Escalation Rules (transparent floors applied after weighted score):", size=10, bold=True, color=NAVY)
    txbox(sl, 0.5, 6.85, 12.3, 0.42,
          "① OD=Total/Critical + DS≥0.9 or PF≥0.9 → CRITICAL  "
          "② OD≥High + DS=1.0 + DV≥50% → CRITICAL  "
          "③ Payment rail (PF=1.0) + DS≥0.6 → CRITICAL  "
          "④ Core banking (PF≥0.9) + OD≥High → CRITICAL  "
          "⑤ Privileged access + OD≥High → HIGH",
          size=9.5, color=DGREY)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 7 — Per-Vendor Results Table
# ══════════════════════════════════════════════════════════════════════════════
def slide_results_table(prs):
    sl = blank(prs)
    rect(sl, 0, 0, 13.33, 7.5, fill=LGREY)
    heading_bar(sl, "Per-Vendor Assessment Results", "6 vendors assessed · V-000 Larkspur = provided worked example (read-only)")
    footer(sl, "7 / 14")

    # Table header
    cols = ["Ref", "Vendor", "Category", "Criticality", "AI Usage", "Risk Class", "Top Recommendation"]
    col_ws = [0.55, 1.9, 2.1, 1.05, 0.9, 1.0, 5.4]
    header_y = 1.25
    rect(sl, 0.2, header_y, 13.0, 0.42, fill=NAVY)
    x = 0.25
    for col, cw in zip(cols, col_ws):
        txbox(sl, x, header_y + 0.05, cw, 0.32, col, size=9.5, bold=True, color=WHITE)
        x += cw

    vendors = [
        ("V-001", "AutomWorx",         "Professional Services",  "HIGH",     "INCONCLUSIVE", "MEDIUM",   "P2: AI-usage questionnaire; public material is inconclusive"),
        ("V-002", "Fiserv",            "Core Platform",           "CRITICAL", "YES",          "HIGH",     "P1: Disclose model providers for Frontier and bureau integrations"),
        ("V-003", "FSSI",              "Document & Communications","MEDIUM",  "INCONCLUSIVE", "LOW",      "P3: Include AI-usage question in next periodic review"),
        ("V-004", "Terrapin Systems",  "Data & Reporting",        "HIGH",     "INCONCLUSIVE", "MEDIUM",   "P2: Questionnaire; marketing claims not corroborated by direct evidence"),
        ("V-005", "BNY",               "Payments",                "CRITICAL", "YES",          "HIGH",     "P1: Disclose Eliza platform scope; confirm no Meridian data trains models"),
        ("V-006", "The Clearing House","Payments Infrastructure",  "CRITICAL", "INCONCLUSIVE", "MEDIUM",  "P2: Questionnaire; RTP fraud-prevention sources temporarily unavailable"),
    ]
    risk_col = {"CRITICAL": RED, "HIGH": ORANGE, "MEDIUM": AMBER, "LOW": GREEN}
    crit_col = {"CRITICAL": RED, "HIGH": ORANGE, "MEDIUM": AMBER, "LOW": GREEN}
    ai_col = {"YES": GREEN, "NO": RED, "INCONCLUSIVE": AMBER}

    for row_i, (ref, name, cat, crit, ai, risk, rec) in enumerate(vendors):
        y = header_y + 0.42 + row_i * 0.72
        bg = WHITE if row_i % 2 == 0 else LGREY
        rect(sl, 0.2, y, 13.0, 0.72, fill=bg)
        txbox(sl, 0.25, y + 0.12, 0.55, 0.48, ref, size=9, bold=True, color=NAVY)
        txbox(sl, 0.8, y + 0.05, 1.85, 0.62, name, size=10.5, bold=True, color=NAVY)
        txbox(sl, 2.65, y + 0.12, 2.05, 0.48, cat, size=9, color=DGREY)

        # Criticality badge
        rect(sl, 4.7, y + 0.14, 0.95, 0.38, fill=crit_col.get(crit, LGREY))
        txbox(sl, 4.71, y + 0.17, 0.93, 0.32, crit, size=9, bold=True, color=WHITE, align=PP_ALIGN.CENTER)

        # AI usage badge
        rect(sl, 5.65, y + 0.14, 0.85, 0.38, fill=ai_col.get(ai, LGREY))
        txbox(sl, 5.66, y + 0.17, 0.83, 0.32, ai, size=8.5, bold=True, color=WHITE, align=PP_ALIGN.CENTER)

        # Risk badge
        rect(sl, 6.5, y + 0.14, 0.9, 0.38, fill=risk_col.get(risk, LGREY))
        txbox(sl, 6.51, y + 0.17, 0.88, 0.32, risk, size=9, bold=True, color=WHITE, align=PP_ALIGN.CENTER)

        txbox(sl, 7.4, y + 0.1, 5.7, 0.52, rec, size=9.5, color=DGREY)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 8 — Deep-Dive: BNY (Critical · YES AI)
# ══════════════════════════════════════════════════════════════════════════════
def slide_deepdive_bny(prs):
    sl = blank(prs)
    rect(sl, 0, 0, 13.33, 7.5, fill=LGREY)
    heading_bar(sl, "Deep-Dive: BNY (V-005)", "Critical · AI Usage = YES · Risk = HIGH")
    footer(sl, "8 / 14")

    # Criticality panel
    rect(sl, 0.3, 1.25, 6.0, 2.65, fill=WHITE)
    txbox(sl, 0.5, 1.33, 5.6, 0.38, "Criticality: CRITICAL (Score ~0.83)", size=12, bold=True, color=RED)
    bullet_list(sl, 0.5, 1.75, 5.7, 2.0, [
        ("OD: Critical (1.0) × 0.30 = 0.300", 0),
        ("DS: Payment instructions (0.8) × 0.25 = 0.200", 0),
        ("PF: Payment rail — RTP network (1.0) × 0.15 = 0.150", 0),
        ("RE: Payment system regulation (0.9) × 0.15 = 0.135", 0),
        ("DV: Transaction volume at scale × 0.15 = ~0.045", 0),
        ("Escalation: Payment rail (PF=1.0) + DS≥0.6 → CRITICAL floor", 1),
    ])

    # AI Usage panel
    rect(sl, 6.5, 1.25, 6.5, 2.65, fill=WHITE)
    txbox(sl, 6.7, 1.33, 6.1, 0.38, "AI Usage: YES", size=12, bold=True, color=GREEN)
    bullet_list(sl, 6.7, 1.75, 6.2, 2.0, [
        ("Eliza — BNY's enterprise AI platform (SERVICE_INTEGRATED)", 0),
        ("Source: bny.com/artificial-intelligence (DIRECT reliability)", 1),
        ("'Our enterprise AI platform, Eliza, is built on the premise of foundational models'", 1),
        ("Providers confirmed: OpenAI (ChatGPT API), Google Gemini Enterprise, NVIDIA AI Supercomputer", 0),
        ("Source: openai.com/index/bny (MEDIUM reliability)", 1),
        ("Fraud detection AI on payment flows (PRODUCT_FEATURE)", 0),
    ])

    # Risk assessment
    rect(sl, 0.3, 4.0, 12.7, 0.38, fill=ORANGE)
    txbox(sl, 0.5, 4.04, 12.3, 0.3, "Risk Classification: HIGH  (Score ~68/100)  — would reach CRITICAL under confirmed_ai_critical_high_data_sensitivity floor if DS≥0.8",
          size=11, bold=True, color=WHITE)

    rect(sl, 0.3, 4.38, 12.7, 2.05, fill=WHITE)
    risk_drivers = [
        ("DATA_EXPOSURE", "HIGH", "Payment instructions + Eliza AI — data sensitivity 0.8 × AI presence"),
        ("AI_SUBPROCESSOR_RISK", "HIGH", "OpenAI & Google disclosed at enterprise level — not service-linked to Meridian workflow"),
        ("MODEL_PROVIDER_TRANSPARENCY", "HIGH", "Providers named but linkage to Meridian's payment service not established"),
        ("DECISION_IMPACT", "HIGH", "Fraud Detection AI (0.9) applied to payment flows — automated decisions"),
        ("CONTRACTUAL_RISK", "UNKNOWN", "No public AI clause data in Meridian contract — scored as unknown (0.7)"),
    ]
    for i, (cat, level, rationale) in enumerate(risk_drivers):
        y = 4.45 + i * 0.38
        c = {"HIGH": ORANGE, "UNKNOWN": RGBColor(0x88, 0x44, 0x44)}.get(level, LGREY)
        rect(sl, 0.35, y, 0.8, 0.3, fill=c)
        txbox(sl, 0.36, y + 0.02, 0.78, 0.26, level, size=8.5, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
        txbox(sl, 1.2, y, 1.8, 0.3, cat, size=9, bold=True, color=NAVY)
        txbox(sl, 3.0, y, 10.0, 0.3, rationale, size=9.5, color=DGREY)

    # Top recommendations
    rect(sl, 0.3, 6.5, 12.7, 0.88, fill=RGBColor(0xE8, 0xF4, 0xFF))
    txbox(sl, 0.5, 6.53, 12.3, 0.3, "Top Recommendations:", size=10, bold=True, color=NAVY)
    txbox(sl, 0.5, 6.83, 12.3, 0.5,
          "P1 · SUBPROCESSOR: Disclose which Eliza components (OpenAI / Gemini) process Meridian payment data and their hosting region  ·  "
          "P1 · DATA_FLOW: Obtain data-flow diagram for AI components touching Meridian transactions  ·  "
          "P2 · TRAINING: Confirm Meridian payment data does not train or fine-tune Eliza or its LLM providers",
          size=9.5, color=DGREY)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 9 — Deep-Dive: AutomWorx (INCONCLUSIVE)
# ══════════════════════════════════════════════════════════════════════════════
def slide_deepdive_automworx(prs):
    sl = blank(prs)
    rect(sl, 0, 0, 13.33, 7.5, fill=LGREY)
    heading_bar(sl, "Deep-Dive: AutomWorx (V-001)", "HIGH Criticality · AI Usage = INCONCLUSIVE — Marketing claims without service-level confirmation")
    footer(sl, "9 / 14")

    rect(sl, 0.3, 1.25, 12.7, 5.1, fill=WHITE)
    txbox(sl, 0.5, 1.33, 12.3, 0.4, "Why INCONCLUSIVE — not YES?", size=13, bold=True, color=ORANGE)

    bullet_list(sl, 0.5, 1.8, 12.0, 4.0, [
        ("AutomWorx markets 'AI-powered automation' — but this alone is insufficient for a YES determination", 0),
        ("YES requires: single confirming signal ≥ 65 strength, OR two confirming signals ≥ 45 each from distinct sources", 1),
        ("A confirming nature is SERVICE_INTEGRATED (AI in the contracted service) or PRODUCT_FEATURE (AI in the product Meridian uses)", 1),
        ("Evidence found classifies as MARKETING_ONLY or INDUSTRY_COMMENTARY:", 0),
        ("Generic AI claims without naming which workload automation features use AI", 1),
        ("No technical documentation or trust-center page confirming AI in the batch-processing or job-scheduling features Meridian uses", 1),
        ("Hiring signals for ML engineers exist, but HIRING_SIGNAL (weight 0.35) cannot alone reach the YES threshold", 1),
        ("What a YES would require:", 0),
        ("A vendor self-statement (DIRECT source) naming AI in the specific workload orchestration or Automic features Meridian subscribes to, OR", 1),
        ("Two MEDIUM-strength confirmations from independent domains (e.g., partner page + investor disclosure)", 1),
        ("Correct classification is: INCONCLUSIVE — absence of public evidence ≠ absence of AI", 0),
        ("MAVIRA's INCONCLUSIVE verdict triggers a P2 questionnaire, not a dismissal", 1),
        ("This is more conservative and more defensible than a YES based on marketing language", 1),
    ])

    rect(sl, 0.3, 6.45, 12.7, 0.9, fill=RGBColor(0xFF, 0xF8, 0xE8))
    txbox(sl, 0.5, 6.5, 12.3, 0.3, "Contrast with Friend's Approach:", size=10, bold=True, color=NAVY)
    txbox(sl, 0.5, 6.8, 12.3, 0.5,
          "A hard-coded YES label based solely on a vendor website mention would be incorrect under our methodology. "
          "MAVIRA's AI classification is evidence-gated: every YES is traceable to a validated exact excerpt from a "
          "classified source with a computed strength score ≥ 45 or ≥ 65.",
          size=9.5, color=DGREY)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 10 — Marketing vs. Real AI: Terrapin
# ══════════════════════════════════════════════════════════════════════════════
def slide_marketing_vs_real(prs):
    sl = blank(prs)
    rect(sl, 0, 0, 13.33, 7.5, fill=LGREY)
    heading_bar(sl, "Distinguishing Marketing AI from Real AI: Terrapin (V-004)",
                "INCONCLUSIVE — AI signals exist but do not tie to the contracted service at sufficient strength")
    footer(sl, "10 / 14")

    # Left: what Terrapin says
    rect(sl, 0.3, 1.25, 6.0, 5.55, fill=WHITE)
    txbox(sl, 0.5, 1.33, 5.6, 0.4, "What Terrapin's Marketing Says", size=12, bold=True, color=AMBER)
    bullet_list(sl, 0.5, 1.8, 5.7, 4.7, [
        ("'AI-powered analytics platform'", 0),
        ("'Leverages machine learning to surface insights'", 0),
        ("'Intelligent compensation reporting'", 0),
        ("'Predictive analytics for advisor performance'", 0),
    ])
    rect(sl, 0.3, 3.9, 6.0, 0.4, fill=AMBER)
    txbox(sl, 0.35, 3.93, 5.9, 0.33, "Classification: MARKETING_ONLY (weight 0.1)", size=10, bold=True, color=WHITE)
    txbox(sl, 0.5, 4.35, 5.7, 2.3,
          "Why marketing? These claims use MODAL language: 'leverages', "
          "'surfaces', 'intelligent' — without concrete production evidence.\n\n"
          "No technical documentation, no trust-center page, no investor disclosure "
          "confirms AI is deployed and actively processing Meridian advisor data.\n\n"
          "Strength score: < 45 (MODERATE threshold). Cannot support YES.",
          size=10.5, color=DGREY)

    # Right: what MAVIRA classifies
    rect(sl, 6.5, 1.25, 6.5, 5.55, fill=WHITE)
    txbox(sl, 6.7, 1.33, 6.1, 0.4, "What MAVIRA Requires for YES", size=12, bold=True, color=GREEN)
    bullet_list(sl, 6.7, 1.8, 6.2, 4.7, [
        ("CONCRETE language: 'is deployed', 'processes', 'already', 'in production', 'uses'", 0),
        ("FIRST-PERSON statement from the vendor itself (DIRECT source)", 0),
        ("SERVICE-SPECIFIC: the claim ties to the compensation/reporting service Meridian uses", 0),
        ("STRENGTH ≥ 65 (STRONG) for a single signal, or ≥ 45 for two signals from distinct domains", 0),
        ("Nature classification: SERVICE_INTEGRATED or PRODUCT_FEATURE", 0),
        ("What WOULD upgrade Terrapin to YES:", 0),
        ("A trust-center or technical doc page stating: 'Terrapin's compensation engine uses ML model X to generate advisor payout calculations'", 1),
        ("OR: SEC 10-K stating AI is live in advisor analytics + a corroborating partner page", 1),
    ])

    rect(sl, 0.3, 6.9, 12.7, 0.45, fill=RGBColor(0xE8, 0xFF, 0xE8))
    txbox(sl, 0.5, 6.93, 12.3, 0.38,
          "MAVIRA protects Meridian from over-disclosure (labelling a non-AI vendor as AI) and under-disclosure (missing genuine AI deployment). "
          "Both errors have regulatory and contractual consequences.",
          size=9.5, color=NAVY)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 11 — Risk Summary
# ══════════════════════════════════════════════════════════════════════════════
def slide_risk_summary(prs):
    sl = blank(prs)
    rect(sl, 0, 0, 13.33, 7.5, fill=LGREY)
    heading_bar(sl, "AI Security Risk Summary", "9-category risk model · standards-grounded floors · transparent rationale")
    footer(sl, "11 / 14")

    # Risk model explanation
    rect(sl, 0.3, 1.25, 8.0, 2.1, fill=WHITE)
    txbox(sl, 0.5, 1.33, 7.6, 0.4, "Risk Model: 9 Categories × AI Presence Index", size=12, bold=True, color=NAVY)
    txbox(sl, 0.5, 1.75, 7.6, 0.35, "Risk Score = 100 × Σ(weight × base × AI_presence)  where  AI_presence = min(1, exposure / 0.6)", size=10.5, color=TEAL)
    categories = [
        "DATA_EXPOSURE (16%) · AI_SUBPROCESSOR_RISK (10%) · MODEL_PROVIDER_TRANSPARENCY (8%)",
        "DATA_RETENTION_RISK (8%) · MODEL_TRAINING_RISK (8%) · DECISION_IMPACT (14%)",
        "OPERATIONAL_DEPENDENCY (14%) · REGULATORY_RISK (12%) · CONTRACTUAL_RISK (10%)",
    ]
    for i, cat in enumerate(categories):
        txbox(sl, 0.5, 2.15 + i * 0.35, 7.6, 0.32, f"• {cat}", size=9.5, color=DGREY)

    # Floor rules
    rect(sl, 8.5, 1.25, 4.5, 2.1, fill=WHITE)
    txbox(sl, 8.7, 1.33, 4.1, 0.4, "Risk Floor Rules", size=12, bold=True, color=RED)
    floors = [
        ("Confirmed AI + Critical vendor + not service-linked provider → HIGH minimum", ORANGE),
        ("Confirmed AI + Critical vendor + data sensitivity ≥ 0.8 → CRITICAL", RED),
        ("Confirmed AI + Critical vendor + Agentic AI detected → CRITICAL", RED),
    ]
    for i, (f_text, f_color) in enumerate(floors):
        rect(sl, 8.5, 1.75 + i * 0.5, 4.5, 0.45, fill=f_color)
        txbox(sl, 8.6, 1.78 + i * 0.5, 4.3, 0.38, f_text, size=8.5, color=WHITE)

    # Per-vendor risk summary table
    rect(sl, 0.3, 3.45, 12.7, 0.4, fill=NAVY)
    for col_i, (txt, w) in enumerate(zip(
            ["Vendor", "AI Usage", "Score", "Classification", "Floor Applied?", "Key Risk Driver"],
            [2.5, 1.0, 0.7, 1.3, 1.5, 5.7])):
        x = 0.35 + sum([2.5, 1.0, 0.7, 1.3, 1.5, 5.7][:col_i])
        txbox(sl, x, 3.48, w - 0.05, 0.34, txt, size=9.5, bold=True, color=WHITE)

    risk_data = [
        ("AutomWorx",          "INCON.", "~18", "MEDIUM",   "No",  "HIRING_SIGNAL only; presence too low for HIGH"),
        ("Fiserv",             "YES",    "~62", "HIGH",     "Yes", "Confirmed AI + Critical + undisclosed provider → HIGH floor; near CRITICAL"),
        ("FSSI",               "INCON.", "~10", "LOW",      "No",  "Weak signal; Medium criticality; low AI presence"),
        ("Terrapin Systems",   "INCON.", "~22", "MEDIUM",   "No",  "Marketing AI only; no service-level confirmation"),
        ("BNY",                "YES",    "~68", "HIGH",     "Yes", "Payment rail + Eliza AI + 3 providers named at enterprise level"),
        ("The Clearing House", "INCON.", "~25", "MEDIUM",   "No",  "Advocacy AI reference only; no product-level AI confirmation"),
    ]
    risk_col_map = {"HIGH": ORANGE, "CRITICAL": RED, "MEDIUM": AMBER, "LOW": GREEN, "MEDIUM": AMBER}
    ai_col_map = {"YES": GREEN, "NO": RED, "INCON.": AMBER}

    for row_i, (name, ai, score, risk, floor, driver) in enumerate(risk_data):
        y = 3.85 + row_i * 0.52
        bg = WHITE if row_i % 2 == 0 else LGREY
        rect(sl, 0.3, y, 12.7, 0.52, fill=bg)
        txbox(sl, 0.35, y + 0.1, 2.45, 0.32, name, size=10, bold=True, color=NAVY)
        rect(sl, 2.85, y + 0.1, 1.0, 0.3, fill=ai_col_map.get(ai, LGREY))
        txbox(sl, 2.86, y + 0.13, 0.98, 0.24, ai, size=9, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
        txbox(sl, 3.85, y + 0.1, 0.65, 0.3, score, size=10, color=DGREY, align=PP_ALIGN.CENTER)
        c = risk_col_map.get(risk, LGREY)
        rect(sl, 4.5, y + 0.1, 1.25, 0.3, fill=c)
        txbox(sl, 4.51, y + 0.13, 1.23, 0.24, risk, size=9, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
        txbox(sl, 5.75, y + 0.1, 1.45, 0.3, floor, size=9.5, color=(RED if floor == "Yes" else GREEN),
              bold=(floor == "Yes"), align=PP_ALIGN.CENTER)
        txbox(sl, 7.2, y + 0.08, 5.7, 0.38, driver, size=9.5, color=DGREY)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 12 — Regulatory Grounding
# ══════════════════════════════════════════════════════════════════════════════
def slide_regulatory(prs):
    sl = blank(prs)
    rect(sl, 0, 0, 13.33, 7.5, fill=LGREY)
    heading_bar(sl, "Regulatory & Standards Grounding", "Every recommendation is anchored to a specific framework citation")
    footer(sl, "12 / 14")

    standards = [
        ("NIST AI RMF\n(2023)", NAVY,
         ["MAP-1.1: AI risk identification in third-party relationships",
          "GV-6.2: Sub-processor and model-provider disclosure",
          "MS-2.5: Data-flow mapping for AI touching personal data",
          "MS-2.6: Model input/output retention",
          "MS-2.8: Ongoing monitoring of AI vendors"]),
        ("FFIEC SR 11-7 /\nOCC 2011-12", TEAL,
         ["Model Risk Management — third-party AI models in-scope",
          "Applies where vendor AI constitutes a 'model' per definition",
          "Meridian may need to extend its MRM programme",
          "Key test: model's output influences Meridian's decisions"]),
        ("OCC 2023-17 /\nOCC 2026-46", RGBColor(0x2E, 0x86, 0xAB),
         ["Third-party arrangements for AI services",
          "§III.C: Sub-processor disclosure obligation",
          "§IV: AI-specific contract clauses required",
          "OCC 2026-46: Ban on training on client data without consent"]),
        ("Fed SR 23-4 /\nCFPB Circular 2022-03", RED,
         ["SR 23-4: Fed guidance on AI in banking",
          "CFPB 2022-03: Explainability for credit decisions",
          "Applies to any AI-driven credit/payment outcome",
          "Agentic AI in payment flows warrants specific attention"]),
        ("NIST CSF 2.0 /\nSP 800-161r1", GREEN,
         ["GV.SC-07: AI supply-chain risk governance",
          "C-SCRM: Cyber supply-chain risk management",
          "All identified AI sub-processors enter the C-SCRM inventory",
          "Incident notification obligations flow to sub-processors"]),
        ("OWASP LLM 2026 /\nAgentic Top-10", ORANGE,
         ["LLM01: Prompt injection — critical for agentic AI vendors",
          "LLM09: Misinformation / over-reliance on model output",
          "Agentic-01: Scope restriction for autonomous agents",
          "Agentic-04: Immutable audit logs for irreversible actions"]),
    ]

    col_w = 4.1
    for i, (name, color, points) in enumerate(standards):
        col = i % 3
        row = i // 3
        x = 0.3 + col * (col_w + 0.1)
        y = 1.3 + row * 2.85
        rect(sl, x, y, col_w, 0.5, fill=color)
        txbox(sl, x + 0.1, y + 0.07, col_w - 0.2, 0.38, name, size=11, bold=True, color=WHITE)
        rect(sl, x, y + 0.5, col_w, 2.25, fill=WHITE)
        for j, pt in enumerate(points):
            txbox(sl, x + 0.1, y + 0.58 + j * 0.42, col_w - 0.2, 0.38, f"• {pt}", size=9.5, color=DGREY)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 13 — Live Demo
# ══════════════════════════════════════════════════════════════════════════════
def slide_demo(prs):
    sl = blank(prs)
    rect(sl, 0, 0, 13.33, 7.5, fill=NAVY)
    rect(sl, 0, 6.5, 13.33, 1.0, fill=TEAL)

    txbox(sl, 0.5, 0.5, 12.3, 0.55, "LIVE DEMO", size=36, bold=True, color=GOLD, align=PP_ALIGN.CENTER)
    txbox(sl, 0.5, 1.2, 12.3, 0.4, "MAVIRA Platform — Meridian AI Vendor Risk Assessment", size=16,
          color=WHITE, align=PP_ALIGN.CENTER)

    demo_steps = [
        ("1", "Run the stack", "docker compose up  →  http://localhost:3000  (FastAPI + Next.js)"),
        ("2", "Import workbook", "Upload the Meridian Excel file  →  6 vendors loaded automatically"),
        ("3", "Run assessment (DEMO)", "Click 'Start Run'  →  watch real-time stage progress per vendor"),
        ("4", "Inspect BNY evidence", "View Eliza evidence chain: exact excerpt · source URL · strength score 78 (STRONG)"),
        ("5", "Check provider list", "OpenAI (enterprise level) · Google Gemini Enterprise · NVIDIA — all detected"),
        ("6", "Export workbook", "Download filled Excel  →  Evidence Log + Sources Checked + Methodology sheets"),
        ("7", "LIVE mode (bonus)", "Set OSINT_MODE=LIVE + SEARCH_PROVIDER=tavily → fresh public OSINT run"),
    ]

    for i, (num, title, desc) in enumerate(demo_steps):
        y = 1.8 + i * 0.68
        rect(sl, 1.0, y, 0.5, 0.5, fill=TEAL)
        txbox(sl, 1.01, y + 0.06, 0.48, 0.38, num, size=16, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
        txbox(sl, 1.6, y + 0.03, 2.8, 0.44, title, size=13, bold=True, color=WHITE)
        txbox(sl, 4.5, y + 0.03, 8.5, 0.44, desc, size=12, color=RGBColor(0xBB, 0xD5, 0xE8))

    txbox(sl, 0.5, 6.6, 12.3, 0.35,
          "docker compose up  ·  http://localhost:3000  ·  Default creds: admin@meridian.com / MeridianAI2026!",
          size=10, bold=True, color=WHITE, align=PP_ALIGN.CENTER)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 14 — Limitations & What We Would Do With More Time
# ══════════════════════════════════════════════════════════════════════════════
def slide_limitations(prs):
    sl = blank(prs)
    rect(sl, 0, 0, 13.33, 7.5, fill=LGREY)
    heading_bar(sl, "Scope, Limitations & Next Steps", "Transparency about what public OSINT can and cannot establish")
    footer(sl, "13 / 14")

    rect(sl, 0.3, 1.25, 6.0, 5.55, fill=WHITE)
    txbox(sl, 0.5, 1.33, 5.6, 0.4, "What Public OSINT Cannot Establish", size=12, bold=True, color=RED)
    bullet_list(sl, 0.5, 1.8, 5.7, 4.7, [
        ("Whether AI features enabled at enterprise level are active in Meridian's specific environment", 0),
        ("What data Meridian's API calls actually send to vendor AI components", 0),
        ("Model training / fine-tuning policies for Meridian data specifically", 0),
        ("Sub-processor chains beyond the first named provider", 0),
        ("Contract AI clauses — not provided as input", 0),
        ("The Clearing House: RTP fraud-prevention AI product pages were temporarily unavailable during collection", 0),
        ("FSSI: Limited AI-specific web presence — result is INCONCLUSIVE, not NO", 0),
        ("AutomWorx: Marketing AI language found; production deployment not confirmed", 0),
    ])

    rect(sl, 6.5, 1.25, 6.5, 5.55, fill=WHITE)
    txbox(sl, 6.7, 1.33, 6.1, 0.4, "With More Time / Resources", size=12, bold=True, color=GREEN)
    bullet_list(sl, 6.7, 1.8, 6.2, 4.7, [
        ("Issue the questionnaire (included as a P2 recommendation for all INCONCLUSIVE vendors)", 0),
        ("Review sub-processor lists for Fiserv and BNY against their disclosed AI providers", 0),
        ("Run in LIVE mode with a search API for fresh, un-cached OSINT", 0),
        ("Engage Meridian's contract team on AI clause gaps identified in this assessment", 0),
        ("Extend MRM programme: determine if Fiserv's Fraud Risk Manager or BNY's Eliza qualify as models under SR 11-7", 0),
        ("Add LLM-assisted evidence proposer (Claude / GPT-4o) for higher evidence recall on long documents", 0),
        ("Automate quarterly reassessment trigger on material vendor AI announcements", 0),
    ])

    rect(sl, 0.3, 6.9, 12.7, 0.45, fill=NAVY)
    txbox(sl, 0.5, 6.93, 12.3, 0.38,
          "This assessment reflects all publicly available information within the OSINT scope as of the collection date. "
          "It is not a substitute for direct vendor questionnaires, contract review, or on-site audit.",
          size=9.5, color=WHITE)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 14 — Q&A / Thank You
# ══════════════════════════════════════════════════════════════════════════════
def slide_qa(prs):
    sl = blank(prs)
    rect(sl, 0, 0, 13.33, 7.5, fill=NAVY)
    rect(sl, 0, 6.0, 13.33, 1.5, fill=TEAL)

    txbox(sl, 0.5, 1.0, 12.3, 0.8, "Thank You", size=48, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    txbox(sl, 0.5, 1.9, 12.3, 0.55, "Questions & Discussion", size=22, color=GOLD, align=PP_ALIGN.CENTER)

    txbox(sl, 0.5, 2.7, 12.3, 0.45,
          "MAVIRA · Meridian AI Vendor Intelligence & Risk Assessment",
          size=14, color=RGBColor(0xBB, 0xD5, 0xE8), align=PP_ALIGN.CENTER)

    callouts = [
        "6 vendors assessed · 2 YES · 0 NO · 4 INCONCLUSIVE",
        "2 HIGH risk (Fiserv, BNY) · 3 MEDIUM · 1 LOW",
        "Methodology v1.1.0 · NIST AI RMF · FFIEC SR 11-7 · OCC 2023-17",
        "Fully offline DEMO mode · SHA-256 hashed evidence · zero hallucinated quotes",
    ]
    for i, c in enumerate(callouts):
        txbox(sl, 0.5, 3.4 + i * 0.5, 12.3, 0.45, f"✓  {c}", size=13, color=WHITE, align=PP_ALIGN.CENTER)

    txbox(sl, 0.5, 5.7, 12.3, 0.45,
          "Team MAVIRA  ·  October 2026  ·  CONFIDENTIAL — NOT FOR DISTRIBUTION",
          size=11, color=WHITE, align=PP_ALIGN.CENTER)
    txbox(sl, 0.5, 6.15, 12.3, 0.45,
          "GitHub: github.com/Santhosh-zeta/optiv-Case1  ·  Run: docker compose up",
          size=11, color=WHITE, align=PP_ALIGN.CENTER)


# ══════════════════════════════════════════════════════════════════════════════
# BUILD
# ══════════════════════════════════════════════════════════════════════════════
def build(out_path: str):
    prs = prs_new()
    slide_title(prs)
    slide_problem(prs)
    slide_how_mavira_works(prs)
    slide_architecture(prs)
    slide_source_strategy(prs)
    slide_criticality(prs)
    slide_results_table(prs)
    slide_deepdive_bny(prs)
    slide_deepdive_automworx(prs)
    slide_marketing_vs_real(prs)
    slide_risk_summary(prs)
    slide_regulatory(prs)
    slide_demo(prs)
    slide_limitations(prs)
    slide_qa(prs)
    prs.save(out_path)
    print(f"Saved {len(prs.slides)} slides -> {out_path}")


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "MAVIRA_Case1_Presentation.pptx"
    build(out)
