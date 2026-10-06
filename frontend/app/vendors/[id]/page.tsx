"use client";
import { useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { PageHeader } from "@/components/shell";
import {
  Button, ErrorNote, Field, Input, Loading, Panel, Select, Table, Tabs, TabsContent, TabsList, TabsTrigger, Td, Textarea, Th,
} from "@/components/ui/primitives";
import { MethodTag, Severity, UsageMark } from "@/components/indicators";
import { EvidenceCard } from "@/components/evidence";
import { useApi } from "@/lib/hooks";
import { api, type AssessmentDetail } from "@/lib/api";
import { cn, fmtDate, pct, titleCase } from "@/lib/utils";

const WEAK_NATURES = ["INDUSTRY_COMMENTARY"];

export default function VendorPage() {
  const { id } = useParams<{ id: string }>();
  const { data: a, error, loading, reload } = useApi<AssessmentDetail>(`/assessments/${id}`);
  if (loading) return <Loading />;
  if (error || !a) return <ErrorNote>{error ?? "Assessment not found"}</ErrorNote>;
  const eff = a.effective ?? {};
  const valid = a.evidence.filter((e) => e.validation_status === "VALID");
  const signals = valid.filter((e) => !WEAK_NATURES.includes(e.nature));

  return (
    <>
      <PageHeader
        title={a.vendor.name}
        sub={<>{a.vendor.vendor_ref}, {a.vendor.category}. Supports <span className="text-ink">{a.vendor.business_process}</span></>}
        actions={<Button variant="secondary" asChild><Link href="/">Back to register</Link></Button>}
      />

      {/* Decision chain: the methodology, read left to right */}
      <ol className="mb-6 grid overflow-hidden rounded-md border border-rule bg-surface sm:grid-cols-2 lg:grid-cols-4">
        <ChainStep n="Criticality" detail={`Score ${a.criticality_score?.toFixed(2)}`}><Severity value={eff.criticality_tier} size="lg" /></ChainStep>
        <ChainStep n="Assessment depth" detail={`${a.negative_evidence?.sources_checked ?? 0} sources, ${a.negative_evidence?.searches_performed ?? 0} searches`}>
          <span className="text-[15px] font-semibold">{a.depth_plan?.label}</span></ChainStep>
        <ChainStep n="AI usage in service" detail={`Confidence ${pct(a.ai_confidence)}`}><UsageMark value={eff.ai_usage} size="lg" /></ChainStep>
        <ChainStep n="AI security risk" detail={`Score ${Math.round(a.risk_score ?? 0)}/100`} last><Severity value={eff.risk_class} size="lg" /></ChainStep>
      </ol>

      {eff.override_reason && (
        <div className="mb-6 rounded-md border border-sev-medium/40 bg-sev-medium-bg px-4 py-3 text-[13px]">
          <span className="font-semibold">Analyst override by {eff.override_by}.</span> {eff.override_reason} Generated values are kept in the review history.
        </div>
      )}

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="evidence">Evidence ({signals.length})</TabsTrigger>
          <TabsTrigger value="risk">Risk</TabsTrigger>
          <TabsTrigger value="sources">Sources and scope</TabsTrigger>
          <TabsTrigger value="review">Analyst review</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          <div className="grid gap-6 lg:grid-cols-2">
            <Panel title="Why this criticality" aside={a.criticality_factors?.escalations.length ? "Escalation rule applied" : undefined}>
              <FactorBars factors={Object.values(a.criticality_factors?.factors ?? {})} />
              {a.criticality_factors?.escalations.map((e) => (
                <p key={e.rule} className="mt-3 text-[13px] text-sev-high">Raised from {titleCase(e.from)} to {titleCase(e.to)}: {e.description}.</p>
              ))}
            </Panel>
            <Panel title="How AI is used" aside={a.provider_status && <span>Model provider {a.provider_status === "not_disclosed" ? "not publicly disclosed" : titleCase(a.provider_status).toLowerCase()}</span>}>
              <p className="text-[13px] leading-relaxed">{eff.ai_usage_summary ?? a.ai_usage_summary}</p>
              <p className="mt-3 text-[12px] text-ink-2">{a.ai_usage_basis}</p>
              {a.ai_types.length > 0 && <p className="mt-3 text-[13px]"><span className="text-ink-3">AI types </span>{a.ai_types.join(", ")}</p>}
              <h3 className="mb-2 mt-5 text-[13px] font-semibold">Named AI providers</h3>
              {a.providers.length === 0
                ? <p className="text-[13px] text-ink-2">None named publicly. This does not establish that no provider is used.</p>
                : <ul className="space-y-3">{a.providers.map((p) => (
                    <li key={p.provider_name} className="text-[13px]">
                      <span className="font-semibold">{p.provider_name}</span>
                      <span className="text-ink-2"> {titleCase(p.provider_type).toLowerCase()}, {p.service_linkage === "SERVICE_LINKED" ? "linked to the contracted service" : "enterprise level only"}, confidence {pct(p.confidence)}</span>
                      <blockquote className="source-fact mt-1 text-[13px]"><mark className="hl">{p.evidence_excerpt}</mark></blockquote>
                    </li>))}</ul>}
            </Panel>
          </div>
          <Panel title="Recommended actions" aside="Generated from rules; each cites the facts it relies on" bodyClass="p-0">
            <Table>
              <thead><tr><Th className="w-16">Priority</Th><Th>Action</Th><Th className="w-28">Due within</Th><Th className="w-32">Area</Th></tr></thead>
              <tbody>{a.recommendations.map((r) => (
                <tr key={r.rule_id}>
                  <Td className={cn("font-semibold", r.priority === "P1" ? "text-sev-critical" : r.priority === "P2" ? "text-sev-high" : "text-ink-2")}>{r.priority}</Td>
                  <Td>{r.action}</Td><Td className="text-ink-2">{r.due_in_days} days</Td><Td className="text-ink-2">{titleCase(r.category)}</Td>
                </tr>))}</tbody>
            </Table>
          </Panel>
          <Panel title="Assessment depth applied">
            <p className="max-w-[80ch] text-[13px] leading-relaxed">{a.depth_plan?.description}</p>
          </Panel>
        </TabsContent>

        <TabsContent value="evidence" className="space-y-4">
          <EvidenceList a={a} />
        </TabsContent>

        <TabsContent value="risk" className="space-y-6">
          <RiskView a={a} />
        </TabsContent>

        <TabsContent value="sources" className="space-y-6">
          <SourcesView a={a} />
        </TabsContent>

        <TabsContent value="review">
          <ReviewView a={a} onDone={reload} />
        </TabsContent>
      </Tabs>

      <p className="mt-8 text-[12px] text-ink-3">
        Run {a.run.id.slice(0, 8)}, methodology {a.run.methodology_version}, analyzer {a.run.analyzer}
        {a.run.prompt_version ? `, prompt ${a.run.prompt_version}` : ""}. Completed {fmtDate(a.completed_at, true)}.
      </p>
    </>
  );
}

function ChainStep({ n, detail, children, last }: { n: string; detail: string; children: React.ReactNode; last?: boolean }) {
  return (
    <li className={cn("relative px-5 py-4", !last && "border-b border-rule-2 lg:border-b-0 lg:border-r")}>
      <div className="text-[12px] text-ink-2">{n}</div>
      <div className="mt-1">{children}</div>
      <div className="mt-1 text-[12px] text-ink-3">{detail}</div>
    </li>
  );
}

function FactorBars({ factors }: { factors: { key: string; label: string; score: number; weight: number; contribution: number; basis: string }[] }) {
  return (
    <ul className="space-y-3">
      {[...factors].sort((x, y) => y.contribution - x.contribution).map((f) => (
        <li key={f.key}>
          <div className="flex justify-between text-[13px]">
            <span className="font-semibold">{f.label}</span>
            <span className="text-ink-2">{f.score.toFixed(2)} × {f.weight.toFixed(2)} = {f.contribution.toFixed(3)}</span>
          </div>
          <div className="mt-1 h-1.5 overflow-hidden rounded bg-rule-2" aria-hidden><div className="h-full bg-ink-2" style={{ width: `${f.score * 100}%` }} /></div>
          <p className="mt-1 text-[12px] text-ink-2">{f.basis}</p>
        </li>
      ))}
    </ul>
  );
}

function EvidenceList({ a }: { a: AssessmentDetail }) {
  const [show, setShow] = useState<"signals" | "all" | "rejected">("signals");
  const list = a.evidence.filter((e) =>
    show === "rejected" ? e.validation_status !== "VALID"
      : e.validation_status === "VALID" && (show === "all" || !WEAK_NATURES.includes(e.nature)));
  const rejected = a.evidence.filter((e) => e.validation_status !== "VALID").length;
  return (
    <>
      <div className="flex flex-wrap items-center gap-3 text-[13px]">
        <label className="flex items-center gap-2">Show
          <Select value={show} onChange={(e) => setShow(e.target.value as typeof show)}>
            <option value="signals">AI signals about the vendor</option>
            <option value="all">All validated excerpts, including commentary</option>
            <option value="rejected">Rejected proposals ({rejected})</option>
          </Select>
        </label>
        <span className="text-ink-3">Every excerpt below was matched character-for-character in the stored source text.</span>
      </div>
      {list.length === 0 && (
        <p className="rounded-md border border-rule bg-surface p-5 text-ink-2">
          {show === "rejected" ? "No proposals were rejected." : a.negative_evidence?.statement
            ? `${a.negative_evidence.statement}. See Sources and scope for what was checked.` : "No excerpts in this view."}
        </p>
      )}
      {list.map((e) => <EvidenceCard key={e.id} e={e} />)}
    </>
  );
}

function RiskView({ a }: { a: AssessmentDetail }) {
  const presence = a.risk_inputs?.result.ai_presence ?? 0;
  return (
    <>
      <Panel title="Risk rationale" aside={`AI presence index ${presence.toFixed(2)}`}>
        <p className="max-w-[85ch] text-[13px] leading-relaxed">{a.effective.risk_rationale ?? a.risk_rationale}</p>
      </Panel>
      <Panel title="Risk categories" aside="Category score = base × AI presence; contribution = score × weight × 100" bodyClass="p-0">
        <Table>
          <thead><tr><Th>Category</Th><Th className="w-48">Score</Th><Th className="w-20">Weight</Th><Th className="w-24">Points</Th><Th>Basis</Th></tr></thead>
          <tbody>{a.risk_factors.map((r) => (
            <tr key={r.category}>
              <Td className="font-semibold">{titleCase(r.category)}</Td>
              <Td>
                <div className="flex items-center gap-2">
                  <div className="h-1.5 w-24 overflow-hidden rounded bg-rule-2" aria-hidden>
                    <div className="h-full" style={{ width: `${r.score * 100}%`, background: r.score >= 0.75 ? "#8E1F1F" : r.score >= 0.5 ? "#B4471A" : r.score >= 0.25 ? "#946A12" : "#4D6E33" }} />
                  </div>
                  <span>{r.score.toFixed(2)}</span>
                </div>
              </Td>
              <Td className="text-ink-2">{r.weight}</Td>
              <Td>{r.contribution.toFixed(1)}</Td>
              <Td className="text-[12px] text-ink-2">
                {r.status.startsWith("UNKNOWN") && <span className="mr-1 font-semibold text-sev-medium">Unknown, not publicly disclosed.</span>}
                {r.rationale}
              </Td>
            </tr>))}</tbody>
        </Table>
      </Panel>
    </>
  );
}

function SourcesView({ a }: { a: AssessmentDetail }) {
  const ne = a.negative_evidence;
  return (
    <>
      {ne?.statement && (
        <div className="rounded-md border border-rule bg-surface px-5 py-4">
          <p className="font-semibold">{ne.statement}</p>
          <p className="mt-1 text-[13px] text-ink-2">{ne.sources_checked} sources checked across {ne.searches_performed} searches. This is a statement about public evidence, not a finding that the vendor does not use AI.</p>
        </div>
      )}
      <Panel title="Sources checked" bodyClass="p-0">
        <Table>
          <thead><tr><Th>Source</Th><Th>Type</Th><Th>Reliability</Th><Th>Collection</Th><Th>Retrieved</Th><Th>AI-relevant passages</Th></tr></thead>
          <tbody>{a.sources.map((s) => (
            <tr key={s.id}>
              <Td><a href={s.url} target="_blank" rel="noopener noreferrer nofollow" className="font-semibold text-pine hover:underline">{s.title || s.domain}</a>
                <div className="break-all text-[12px] text-ink-3">{s.url}</div></Td>
              <Td className="text-ink-2">{titleCase(s.source_type)}</Td>
              <Td>{titleCase(s.reliability_level)}</Td>
              <Td><MethodTag value={s.collection_method} /></Td>
              <Td className="whitespace-nowrap text-ink-2">{fmtDate(s.retrieved_at)}</Td>
              <Td>{s.ai_relevant_chunks ?? 0}</Td>
            </tr>))}</tbody>
        </Table>
      </Panel>
      <Panel title="Search strategy executed" aside={`${a.depth_plan?.tier ? titleCase(a.depth_plan.tier) : ""} tier scope`} bodyClass="p-0">
        <Table>
          <thead><tr><Th>Category</Th><Th>Query</Th><Th>Provider</Th><Th>Results</Th><Th>Status</Th></tr></thead>
          <tbody>{a.searches.map((s, i) => (
            <tr key={i}>
              <Td className="text-ink-2">{titleCase(s.category)}</Td>
              <Td className="break-all">{s.query}</Td>
              <Td className="text-ink-2">{s.provider}</Td>
              <Td>{s.result_count}</Td>
              <Td className={s.status === "OK" ? "text-pine" : "text-sev-critical"}>{s.status === "OK" ? "OK" : s.error}</Td>
            </tr>))}</tbody>
        </Table>
      </Panel>
    </>
  );
}

function ReviewView({ a, onDone }: { a: AssessmentDetail; onDone: () => void }) {
  const router = useRouter();
  const [decision, setDecision] = useState<"APPROVE" | "OVERRIDE" | "REQUEST_REASSESSMENT">("APPROVE");
  const [analyst, setAnalyst] = useState("");
  const [reason, setReason] = useState("");
  const [ov, setOv] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const canReview = a.status === "COMPLETED" || a.status === "PARTIAL";

  async function submit() {
    setBusy(true); setMsg(null);
    try {
      const overrides = Object.fromEntries(Object.entries(ov).filter(([, v]) => v));
      const r = await api.post<{ review_status: string; reassessment_run_id: string | null }>(`/assessments/${a.id}/reviews`,
        { decision, analyst, reason: reason || null, overrides: decision === "OVERRIDE" ? overrides : null });
      if (r.reassessment_run_id) { router.push(`/runs/${r.reassessment_run_id}`); return; }
      setMsg({ ok: true, text: decision === "APPROVE" ? "Assessment approved." : "Override recorded. The generated result is preserved in history." });
      setReason(""); setOv({});
      onDone();
    } catch (e) {
      setMsg({ ok: false, text: (e as Error).message });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[3fr_2fr]">
      <Panel title="Record a decision" aside={a.human_review_required ? <span className="text-sev-high">Analyst sign-off required for this tier or risk</span> : undefined}>
        {!canReview ? <p className="text-ink-2">Review opens when the assessment completes.</p> : (
          <div className="space-y-4">
            <fieldset className="flex flex-wrap gap-2" aria-label="Decision">
              {([["APPROVE", "Approve"], ["OVERRIDE", "Override"], ["REQUEST_REASSESSMENT", "Request reassessment"]] as const).map(([k, l]) => (
                <button key={k} type="button" onClick={() => setDecision(k)} aria-pressed={decision === k}
                  className={cn("rounded-[5px] border px-3 py-1.5 text-[13px] font-semibold",
                    decision === k ? "border-pine bg-pine-2 text-pine" : "border-rule text-ink-2 hover:bg-rule-2")}>{l}</button>
              ))}
            </fieldset>
            <Field label="Analyst name"><Input value={analyst} onChange={(e) => setAnalyst(e.target.value)} placeholder="Your name" maxLength={120} /></Field>
            {decision === "OVERRIDE" && (
              <div className="grid gap-3 sm:grid-cols-3">
                <Field label="Criticality">
                  <Select className="w-full" value={ov.criticality_tier ?? ""} onChange={(e) => setOv({ ...ov, criticality_tier: e.target.value })}>
                    <option value="">Keep {titleCase(a.criticality_tier)}</option>{["CRITICAL", "HIGH", "MEDIUM", "LOW"].map((t) => <option key={t} value={t}>{titleCase(t)}</option>)}
                  </Select></Field>
                <Field label="AI usage">
                  <Select className="w-full" value={ov.ai_usage ?? ""} onChange={(e) => setOv({ ...ov, ai_usage: e.target.value })}>
                    <option value="">Keep {titleCase(a.ai_usage)}</option>{["YES", "NO", "INCONCLUSIVE"].map((t) => <option key={t} value={t}>{titleCase(t)}</option>)}
                  </Select></Field>
                <Field label="AI security risk">
                  <Select className="w-full" value={ov.risk_class ?? ""} onChange={(e) => setOv({ ...ov, risk_class: e.target.value })}>
                    <option value="">Keep {titleCase(a.risk_class)}</option>{["CRITICAL", "HIGH", "MEDIUM", "LOW", "NONE_IDENTIFIED"].map((t) => <option key={t} value={t}>{titleCase(t)}</option>)}
                  </Select></Field>
              </div>
            )}
            <Field label={decision === "APPROVE" ? "Comment (optional)" : "Reason"} hint={decision === "OVERRIDE" ? "Required. At least 10 characters; recorded in the audit trail and the exported workbook." : undefined}>
              <Textarea rows={4} value={reason} onChange={(e) => setReason(e.target.value)} maxLength={4000} />
            </Field>
            {msg && <p role="status" className={msg.ok ? "text-pine" : "text-sev-critical"}>{msg.text}</p>}
            <Button onClick={submit} disabled={busy || !analyst.trim()}>
              {busy ? "Saving…" : decision === "APPROVE" ? "Approve assessment" : decision === "OVERRIDE" ? "Record override" : "Request reassessment"}
            </Button>
          </div>
        )}
      </Panel>
      <Panel title="Review history">
        {a.reviews.length === 0 ? <p className="text-ink-2">No decisions recorded yet. Status: {titleCase(a.review_status)}.</p> : (
          <ol className="space-y-4">
            {[...a.reviews].reverse().map((r) => (
              <li key={r.id} className="border-l-2 border-rule pl-3 text-[13px]">
                <div className="font-semibold">{titleCase(r.decision)} by {r.analyst}</div>
                <div className="text-[12px] text-ink-3">{fmtDate(r.created_at, true)}</div>
                {r.reason && <p className="mt-1">{r.reason}</p>}
                {r.overrides && <p className="mt-1 text-ink-2">Changed: {Object.entries(r.overrides).map(([k, v]) => `${titleCase(k)} to ${titleCase(v)}`).join("; ")}. Original: {String(r.original_snapshot.risk_class ?? "")} risk, {String(r.original_snapshot.ai_usage ?? "")} AI usage.</p>}
                {r.reassessment_run_id && <Link className="mt-1 inline-block text-pine hover:underline" href={`/runs/${r.reassessment_run_id}`}>Open reassessment run</Link>}
              </li>
            ))}
          </ol>
        )}
      </Panel>
    </div>
  );
}

