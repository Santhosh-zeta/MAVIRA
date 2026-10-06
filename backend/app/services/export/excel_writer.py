"""Writes findings back into the original Meridian workbook.

- Provided (blue-grey) columns and the V-000 worked example are never written.
- Only the student (cream) assessment columns of assessed vendor rows change;
  existing cell styles are preserved because values are written in place.
- Adds 'Evidence Log', 'Sources Checked' and 'Methodology' sheets (the worked
  example refers to an Evidence Log sheet).
- Uses the *effective* result: analyst overrides win, and the reviewer is named.
"""
from __future__ import annotations

import io
from datetime import datetime

from openpyxl import load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Assessment, WorkbookImport
from app.services.export.serializers import assessment_detail

HEADER_FILL = PatternFill("solid", fgColor="2E2E2E")
HEADER_FONT = Font(bold=True, color="FFFFFF", name="Calibri", size=10)
BODY_FONT = Font(name="Calibri", size=10)
THIN = Side(style="thin", color="BFBFBF")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(wrap_text=True, vertical="top")
OUT_HEADERS = {
    "criticality_tier": "Criticality Tier", "criticality_rationale": "Criticality Rationale",
    "assessment_depth": "Assessment Depth Applied", "ai_usage": "AI Usage Detected (Y/N)",
    "evidence": "Evidence Description along with OSINT Source(s) / Evidence Link",
    "how_using_ai": "How Vendor May Be Using AI", "ai_providers": "Named AI Sub-processors / Model Providers",
    "risk_class": "AI Security Risk Classification", "risk_rationale": "Risk Rationale",
    "recommended_action": "Recommended Action", "assessed_by": "Assessed By / Date",
}
SIGNAL_NATURES = {"SERVICE_INTEGRATED", "PRODUCT_FEATURE", "PARTNER_DEPENDENCY", "INTERNAL_OPERATIONAL_USE",
                  "HIRING_SIGNAL", "MARKETING_ONLY"}


def _d(iso: str | None) -> str:
    if not iso:
        return "n/a"
    try:
        return datetime.fromisoformat(iso).strftime("%d-%m-%Y")
    except ValueError:
        return iso[:10]


def _title(v: str | None) -> str:
    if not v:
        return ""
    return "None identified" if v == "NONE_IDENTIFIED" else v.replace("_", " ").title()


def build_cells(d: dict, team: str) -> dict[str, str]:
    eff = d["effective"]
    ev = [e for e in d["evidence"] if e["validation_status"] == "VALID" and e["nature"] in SIGNAL_NATURES]
    ev.sort(key=lambda e: -(e["strength_score"] or 0))
    neg = d["negative_evidence"] or {}
    lines = []
    for e in ev[:6]:
        s = e["source"]
        lines.append(f"\"{e['exact_excerpt']}\" — {s['url']} (retrieved {_d(s['retrieved_at'])}; "
                     f"{s['source_type']}; {s['collection_method']})")
    if not lines:
        urls = "; ".join(x["url"] for x in neg.get("sources", [])) or "none reachable"
        lines.append(f"{neg.get('statement') or 'No AI usage excerpt identified'}. Sources checked "
                     f"({neg.get('sources_checked', 0)}): {urls}. Searches performed: {neg.get('searches_performed', 0)}.")
    elif eff.get("ai_usage") != "YES":
        lines.append(f"Scope: {neg.get('sources_checked', 0)} sources checked, {neg.get('searches_performed', 0)} searches performed.")

    provs = d["providers"]
    if provs:
        prov = "; ".join(
            f"{p['provider_name']} — {p['provider_type'].replace('_', ' ').lower()}, "
            f"{'linked to the contracted service' if p['service_linkage'] == 'SERVICE_LINKED' else 'named at enterprise level; linkage to the Meridian service not established'}"
            f" (evidence: \"{p['evidence_excerpt'][:160]}{'…' if len(p['evidence_excerpt']) > 160 else ''}\")"
            for p in provs)
    else:
        prov = ("None named — NOT PUBLICLY DISCLOSED. No model provider or AI sub-processor is identified in the "
                "assessed public sources; this does not establish that none is used.")

    recs = d["recommendations"]
    rec_text = eff.get("recommended_action") or "\n".join(
        f"{i}. [{r['priority']} · within {r['due_in_days']} days] {r['action']}" for i, r in enumerate(recs, 1))
    rationale = eff.get("risk_rationale") or d["risk_rationale"]
    if eff.get("override_reason"):
        rationale = f"{rationale}\nAnalyst override by {eff.get('override_by')}: {eff['override_reason']}"

    status = {"APPROVED": "approved", "OVERRIDDEN": "approved with override"}.get(d["review_status"])
    assessed = f"{team} / {_d(d['completed_at'])}"
    assessed += f"; reviewed by {eff.get('reviewed_by')} ({status}, {_d(eff.get('reviewed_at'))})" if status \
        else "; pending analyst review"

    ai_usage = {"YES": "Yes", "NO": "No", "INCONCLUSIVE": "Inconclusive"}.get(eff.get("ai_usage"), "")
    return {
        "criticality_tier": _title(eff.get("criticality_tier")),
        "criticality_rationale": d["criticality_rationale"] + (
            f" Analyst override to {_title(eff['criticality_tier'])}." if eff.get("criticality_tier") != d["criticality_tier"] else ""),
        "assessment_depth": (d["depth_plan"] or {}).get("description", "") +
                            f" Executed: {neg.get('sources_checked', 0)} sources checked across {neg.get('searches_performed', 0)} searches"
                            f" ({d['run']['osint_mode']} mode; analyzer {d['run']['analyzer']}).",
        "ai_usage": ai_usage,
        "evidence": "\n".join(lines),
        "how_using_ai": eff.get("ai_usage_summary") or d["ai_usage_summary"] or "",
        "ai_providers": prov,
        "risk_class": _title(eff.get("risk_class")),
        "risk_rationale": rationale or "",
        "recommended_action": rec_text,
        "assessed_by": assessed,
    }


def _style_header(ws, headers: list[str], widths: list[int]):
    ws.append(headers)
    for i, w in enumerate(widths, 1):
        c = ws.cell(1, i)
        c.fill, c.font, c.alignment, c.border = HEADER_FILL, HEADER_FONT, WRAP, BORDER
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A2"


def _append(ws, row: list):
    ws.append(row)
    for c in ws[ws.max_row]:
        c.font, c.alignment, c.border = BODY_FONT, WRAP, BORDER


def export_workbook(db: Session, imp: WorkbookImport, assessments: list[Assessment], methodology_cfg: dict) -> bytes:
    team = get_settings().assessor_team
    wb = load_workbook(imp.stored_path)
    ws = wb[imp.sheet_name]
    cmap = imp.column_map
    details = [assessment_detail(db, a) for a in assessments if a.status in ("COMPLETED", "PARTIAL")]
    by_ref = {d["vendor"]["vendor_ref"]: d for d in details}

    # Append any assessment column missing from the header row
    next_col = ws.max_column + 1
    for key, header in OUT_HEADERS.items():
        if f"out:{key}" not in cmap:
            ws.cell(imp.header_row, next_col, header)
            cmap = {**cmap, f"out:{key}": next_col}
            next_col += 1

    ref_col = cmap["vendor_ref"]
    for r in range(imp.header_row + 1, ws.max_row + 1):
        ref = ws.cell(r, ref_col).value
        if not ref or str(ref).strip().upper() == "V-000":
            continue                                    # never touch the worked example
        d = by_ref.get(str(ref).strip())
        if not d:
            continue
        for key, value in build_cells(d, team).items():
            cell = ws.cell(r, cmap[f"out:{key}"])
            cell.value = value
            cell.alignment = Alignment(wrap_text=True, vertical="top")

    # Evidence Log ------------------------------------------------------
    for name in ("Evidence Log", "Sources Checked", "Methodology"):
        if name in wb.sheetnames:
            del wb[name]
    el = wb.create_sheet("Evidence Log")
    _style_header(el, ["Vendor ID", "Vendor", "Evidence ID", "Exact Excerpt (source fact)", "Source URL", "Source Type",
                       "Reliability", "Collection Method", "Retrieved", "Published", "Signal Nature",
                       "AI Types", "Evidence Strength", "Strength Level", "Classification Confidence",
                       "Interpretation (system-generated)", "Validation"],
                  [9, 18, 14, 60, 40, 22, 11, 13, 11, 11, 20, 22, 10, 12, 12, 60, 10])
    for d in details:
        for e in d["evidence"]:
            if e["validation_status"] != "VALID":
                continue
            s = e["source"]
            _append(el, [d["vendor"]["vendor_ref"], d["vendor"]["name"], e["id"][:12], e["exact_excerpt"], s["url"],
                         s["source_type"], s["reliability_level"], s["collection_method"], _d(s["retrieved_at"]),
                         s["published_date"] or "n/a", e["nature"], ", ".join(e["ai_types"]), e["strength_score"],
                         e["strength_level"], e["confidence"], e["interpretation"], "Exact match"])

    sc = wb.create_sheet("Sources Checked")
    _style_header(sc, ["Vendor ID", "Vendor", "Search Category", "URL", "Title", "Source Type", "Reliability",
                       "Collection Method", "Retrieved", "Status", "AI-relevant Chunks"],
                  [9, 18, 18, 50, 40, 22, 11, 13, 11, 10, 10])
    for d in details:
        for s in d["sources"]:
            _append(sc, [d["vendor"]["vendor_ref"], d["vendor"]["name"], s["category"], s["url"], s["title"],
                         s["source_type"], s["reliability_level"], s["collection_method"], _d(s["retrieved_at"]),
                         s["status"], s["ai_relevant_chunks"]])

    me = wb.create_sheet("Methodology")
    _style_header(me, ["Section", "Item", "Value"], [24, 40, 60])
    run = details[0]["run"] if details else {}
    _append(me, ["Run", "Methodology version", run.get("methodology_version", "")])
    _append(me, ["Run", "OSINT mode", run.get("osint_mode", "")])
    _append(me, ["Run", "Analyzer", run.get("analyzer", "")])
    for sect in ("criticality", "risk", "evidence_strength"):
        for k, v in methodology_cfg[sect]["weights"].items():
            _append(me, [f"{sect} weight", k, v])
        for k, v in methodology_cfg[sect].get("thresholds", methodology_cfg[sect].get("levels", {})).items():
            _append(me, [f"{sect} threshold", k, v])
    for tier, t in methodology_cfg["assessment_depth"]["tiers"].items():
        _append(me, ["assessment depth", f"{tier} — {t['label']}", t["rationale"].strip()])
    _append(me, ["note", "Collection methods", "LIVE = fetched during the run; CACHED = verbatim snapshot captured "
                                                "in an earlier analyst session (retrieval date shown); DEMO_MOCK = fictional test data."])

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
