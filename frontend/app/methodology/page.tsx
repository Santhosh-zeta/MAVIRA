"use client";
import { useState } from "react";
import { PageHeader } from "@/components/shell";
import { Button, ErrorNote, Field, Input, Loading, Panel, Table, Td, Textarea, Th } from "@/components/ui/primitives";
import { useApi } from "@/lib/hooks";
import { api } from "@/lib/api";
import { fmtDate, titleCase } from "@/lib/utils";

/* eslint-disable @typescript-eslint/no-explicit-any */
interface Meth {
  active: { id: string; label: string; created_at: string; created_by: string; note: string | null; config: any; yaml: string };
  versions: { id: string; label: string; is_active: boolean; created_at: string; created_by: string; note: string | null }[];
}

function WeightTable({ title, weights, thresholds, note }: { title: string; weights: Record<string, number>; thresholds?: Record<string, number>; note?: string }) {
  return (
    <Panel title={title} aside={note} bodyClass="p-0">
      <Table>
        <thead><tr><Th>Factor</Th><Th className="w-48">Weight</Th></tr></thead>
        <tbody>{Object.entries(weights).map(([k, v]) => (
          <tr key={k}><Td>{titleCase(k)}</Td>
            <Td><div className="flex items-center gap-2"><div className="h-1.5 w-24 overflow-hidden rounded bg-rule-2"><div className="h-full bg-pine" style={{ width: `${v * 100}%` }} /></div>{v}</div></Td></tr>))}</tbody>
      </Table>
      {thresholds && (
        <div className="border-t border-rule-2 px-5 py-3 text-[13px]">
          <span className="font-semibold">Thresholds </span>
          {Object.entries(thresholds).map(([k, v], i) => <span key={k} className="text-ink-2">{i ? ", " : ""}{titleCase(k)} at {v} or above</span>)}
        </div>
      )}
    </Panel>
  );
}

export default function MethodologyPage() {
  const { data, error, loading, reload } = useApi<Meth>("/methodology");
  const [editing, setEditing] = useState(false);
  const [yaml, setYaml] = useState("");
  const [note, setNote] = useState("");
  const [who, setWho] = useState("");
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  if (loading) return <Loading />;
  if (error || !data) return <ErrorNote>{error ?? "Unavailable"}</ErrorNote>;
  const c = data.active.config;

  async function save() {
    setMsg(null);
    try {
      const r = await api.put<{ label: string }>("/methodology", { yaml, note }, who || undefined);
      setMsg({ ok: true, text: `Version ${r.label} is now active. New runs use it; earlier assessments keep their original version.` });
      setEditing(false);
      reload();
    } catch (e) {
      setMsg({ ok: false, text: (e as Error).message });
    }
  }

  return (
    <>
      <PageHeader title="Methodology"
        sub={<>Every weight, threshold and rule the engines use. Active version <span className="font-semibold text-ink">{data.active.label}</span>, set {fmtDate(data.active.created_at, true)} by {data.active.created_by}. The language model, when enabled, never sets a score.</>}
        actions={<Button variant="secondary" onClick={() => { setYaml(data.active.yaml); setEditing(!editing); }}>{editing ? "Close editor" : "Edit as new version"}</Button>}
      />
      {msg && <p role="status" className={`mb-4 ${msg.ok ? "text-pine" : "text-sev-critical"}`}>{msg.text}</p>}
      {editing && (
        <Panel title="Edit methodology" className="mb-6" aside="Weights must sum to 1.0; thresholds run highest to lowest">
          <div className="space-y-4">
            <Textarea rows={22} value={yaml} onChange={(e) => setYaml(e.target.value)} className="font-[monospace] text-[12px]" spellCheck={false} aria-label="Methodology YAML" />
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Change note"><Input value={note} onChange={(e) => setNote(e.target.value)} placeholder="What changed and why" /></Field>
              <Field label="Your name"><Input value={who} onChange={(e) => setWho(e.target.value)} /></Field>
            </div>
            <Button onClick={save} disabled={note.trim().length < 3}>Activate new version</Button>
          </div>
        </Panel>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <WeightTable title="Criticality weights" weights={c.criticality.weights} thresholds={c.criticality.thresholds} note="Inputs come only from the inventory" />
        <WeightTable title="AI security risk weights" weights={c.risk.weights} thresholds={c.risk.thresholds} note="Score out of 100" />
        <WeightTable title="Evidence strength" weights={c.evidence_strength.weights} thresholds={c.evidence_strength.levels} note="Separate from classification confidence" />
        <Panel title="Source reliability" bodyClass="p-0">
          <Table>
            <thead><tr><Th>Level</Th><Th>Weight</Th><Th>Examples</Th></tr></thead>
            <tbody>{Object.entries(c.source_reliability.levels as Record<string, number>).map(([lvl, w]) => (
              <tr key={lvl}><Td className="font-semibold">{titleCase(lvl)}</Td><Td>{w}</Td>
                <Td className="text-[12px] text-ink-2">{[...new Set((c.source_reliability.rules as any[]).filter((r) => r.level === lvl).map((r) => titleCase(r.source_type)))].join(", ")}</Td></tr>))}</tbody>
          </Table>
        </Panel>
      </div>

      <Panel title="Assessment depth by criticality tier" className="mt-6" bodyClass="p-0">
        <Table>
          <thead><tr><Th>Tier</Th><Th>Depth</Th><Th>Why</Th><Th>Source categories</Th><Th>Max sources</Th><Th>Sign-off</Th></tr></thead>
          <tbody>{(["LOW", "MEDIUM", "HIGH", "CRITICAL"]).map((t) => {
            const d = c.assessment_depth.tiers[t];
            return (
              <tr key={t}><Td className="font-semibold">{titleCase(t)}</Td><Td>{d.label}</Td><Td className="max-w-[36ch] text-[12px] text-ink-2">{d.rationale}</Td>
                <Td className="text-[12px] text-ink-2">{(d.source_categories as string[]).map(titleCase).join(", ")}</Td>
                <Td>{d.max_sources}</Td><Td>{d.human_review_required ? "Required" : "Optional"}</Td></tr>);
          })}</tbody>
        </Table>
      </Panel>

      <Panel title="Signal types" className="mt-6" aside="Weight feeds AI exposure; only the first two can confirm AI use" bodyClass="p-0">
        <Table>
          <thead><tr><Th>Signal</Th><Th>Exposure weight</Th></tr></thead>
          <tbody>{Object.entries(c.ai_classification.nature_weights as Record<string, number>).map(([k, v]) => (
            <tr key={k}><Td>{titleCase(k)}</Td><Td>{v}</Td></tr>))}</tbody>
        </Table>
      </Panel>

      <Panel title="Version history" className="mt-6" bodyClass="p-0">
        <Table>
          <thead><tr><Th>Version</Th><Th>Created</Th><Th>By</Th><Th>Note</Th><Th>Status</Th></tr></thead>
          <tbody>{data.versions.map((v) => (
            <tr key={v.id}><Td className="font-semibold">{v.label}</Td><Td>{fmtDate(v.created_at, true)}</Td><Td>{v.created_by}</Td>
              <Td className="text-ink-2">{v.note}</Td><Td>{v.is_active ? <span className="text-pine">Active</span> : "Superseded"}</Td></tr>))}</tbody>
        </Table>
      </Panel>
    </>
  );
}
