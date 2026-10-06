# Stakeholder walkthrough (12 minutes)

Start state: stack running in DEMO mode, empty database (`docker compose down -v && docker compose up`).

| Time | Screen | Say / show |
|---|---|---|
| 0:00 | Vendor register (empty) | The problem: six vendors, decide which ones use AI in what they deliver to Meridian and what that means for risk. Sidebar shows the mode: cached OSINT snapshot, no LLM — nothing leaves this machine. |
| 1:00 | Import workbook | Drop the Meridian workbook. Columns matched by header, V-000 recognised and left untouched, six vendors ready. Mention validation catches missing columns and duplicate IDs. |
| 2:00 | Run | Start assessment. Twelve stages per vendor, live. Point out criticality and depth are decided before any search. |
| 3:30 | Register | Criticality distribution: three Critical, two High, one Medium. Two vendors confirmed AI, four inconclusive. Sign-off required on Critical / High risk. |
| 4:30 | Fiserv → Overview | Decision chain. Criticality 0.98 — every factor with its matched rule. Depth: Full review. AI usage Yes 76%, explicitly vendor-level, DNA not named. Microsoft named at enterprise level only. |
| 6:00 | Fiserv → Evidence | Source fact vs interpretation. Open "View in source": the excerpt is highlighted inside the stored page text. Expand "How strength was scored". Show the forward-looking statement about third-party AI model safeguards — drives an assurance recommendation. |
| 7:30 | Fiserv → Risk | Nine categories; unknowns labelled "not publicly disclosed", never assumed safe. Vendor-level discount and the Critical-vendor floor explained in the rationale. |
| 8:30 | The Clearing House | Critical vendor, no AI signal: "No meaningful public evidence identified within assessed OSINT scope", sources and searches listed. Risk None identified — not "No AI". Questionnaire recommended. |
| 9:30 | AutomWorx | Escalated Medium → High for privileged production access. AI lives in the Automic platform it implements ("bring your own LLM"); recommendation to check what is enabled and where logs go. |
| 10:30 | Review | Approve Fiserv. Override Terrapin with a reason — generated result kept in history. |
| 11:15 | Export | Export completed workbook: V-000 untouched, cream columns filled, Evidence Log / Sources Checked / Methodology sheets. |
| 11:45 | Methodology / Audit | Weights and tiers are configuration, versioned; audit trail shows every action. Close on LIVE mode: same pipeline with a search key. |
