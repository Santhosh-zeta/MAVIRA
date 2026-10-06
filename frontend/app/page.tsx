"use client";
import Link from "next/link";
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Download } from "lucide-react";
import { PageHeader } from "@/components/shell";
import { Button, Empty, ErrorNote, Loading, Panel, Table, Td, Th } from "@/components/ui/primitives";
import { Severity, StrengthBar, UsageMark } from "@/components/indicators";
import { useApi } from "@/lib/hooks";
import type { Dashboard } from "@/lib/api";
import { fmtDate, pct, titleCase } from "@/lib/utils";

const SEV_COLORS: Record<string, string> = {
  CRITICAL: "#8E1F1F", HIGH: "#B4471A", MEDIUM: "#946A12", LOW: "#4D6E33", NONE_IDENTIFIED: "#9AA7A9",
};
const TIER_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW"];
const RISK_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "NONE_IDENTIFIED"];

function Distribution({ data, order }: { data: Record<string, number>; order: string[] }) {
  const rows = order.map((k) => ({ key: k, label: titleCase(k), n: data[k] ?? 0 }));
  return (
    <div className="h-[170px]" role="img" aria-label={rows.map((r) => `${r.label}: ${r.n}`).join(", ")}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} layout="vertical" margin={{ left: 0, right: 16, top: 4, bottom: 4 }}>
          <XAxis type="number" allowDecimals={false} hide />
          <YAxis type="category" dataKey="label" width={104} tick={{ fontSize: 12, fill: "#4A5A5E" }} axisLine={false} tickLine={false} />
          <Tooltip cursor={{ fill: "#E8ECEA" }} contentStyle={{ fontSize: 12, border: "1px solid #D6DCD9", borderRadius: 4 }}
            formatter={(v) => [v as number, "Vendors"]} />
          <Bar dataKey="n" barSize={14} radius={[0, 2, 2, 0]} label={{ position: "right", fontSize: 12, fill: "#1E2A2D" }}>
            {rows.map((r) => <Cell key={r.key} fill={SEV_COLORS[r.key]} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export default function DashboardPage() {
  const { data, error, loading } = useApi<Dashboard>("/dashboard", { pollMs: 5000 });
  if (loading) return <Loading />;
  if (error) return <ErrorNote>{error}</ErrorNote>;
  if (!data || !data.import) {
    return (
      <>
        <PageHeader title="Vendor register" />
        <Empty title="No vendor inventory imported yet"
          action={<Button asChild><Link href="/import">Import the Meridian workbook</Link></Button>}>
          Import the vendor inventory workbook to calculate criticality, run the OSINT assessment and review AI risk per vendor.
        </Empty>
      </>
    );
  }
  const t = data.totals;
  const running = data.recent_runs.find((r) => r.status === "RUNNING" || r.status === "QUEUED");
  return (
    <>
      <PageHeader
        title="Vendor register"
        sub={<>From <span className="font-semibold text-ink">{data.import.filename}</span>, imported {fmtDate(data.import.uploaded_at, true)}.</>}
        actions={t.assessed > 0 && (
          <>
            <Button variant="secondary" asChild><a href={`/api/exports/json?import_id=${data.import.id}`}>Export JSON</a></Button>
            <Button asChild><a href={`/api/exports/excel?import_id=${data.import.id}`}><Download size={15} aria-hidden /> Export completed workbook</a></Button>
          </>
        )}
      />

      {running && (
        <Link href={`/runs/${running.id}`} className="mb-5 block rounded-md border border-pine/40 bg-pine-2 px-4 py-3 text-[13px] text-pine hover:underline">
          Assessment in progress: {running.completed_vendors} of {running.total_vendors} vendors complete. View progress
        </Link>
      )}

      <dl className="mb-6 grid grid-cols-2 border-y border-rule bg-surface sm:grid-cols-3 lg:grid-cols-6">
        {[
          ["Vendors in inventory", t.vendors],
          ["Assessed", t.assessed],
          ["AI use confirmed", t.ai_confirmed],
          ["AI use inconclusive", t.ai_inconclusive],
          ["High or critical AI risk", t.high_critical_risk],
          ["Awaiting analyst review", t.pending_review],
        ].map(([label, v], i) => (
          <div key={label as string} className={`px-4 py-3 ${i ? "border-l border-rule-2" : ""}`}>
            <dt className="text-[12px] text-ink-2">{label}</dt>
            <dd className="text-[22px] font-semibold leading-tight">{v}</dd>
          </div>
        ))}
      </dl>

      <Panel title="Assessed vendors" aside="Latest assessment per vendor; analyst overrides applied" bodyClass="p-0">
        <Table>
          <thead>
            <tr>
              <Th>Vendor</Th><Th>Criticality</Th><Th>AI usage</Th><Th>Confidence</Th><Th>AI security risk</Th>
              <Th>Evidence strength</Th><Th>Review</Th><Th>Last assessed</Th>
            </tr>
          </thead>
          <tbody>
            {data.vendors.map((v) => {
              const e = v.effective ?? {};
              const done = v.status === "COMPLETED" || v.status === "PARTIAL";
              return (
                <tr key={v.id} className="hover:bg-paper">
                  <Td>
                    <Link href={`/vendors/${v.id}`} className="font-semibold text-ink hover:text-pine hover:underline">{v.vendor_name}</Link>
                    <div className="text-[12px] text-ink-3">{v.vendor_ref}, {v.category}</div>
                  </Td>
                  <Td><Severity value={e.criticality_tier ?? v.criticality_tier} /></Td>
                  <Td><UsageMark value={done ? e.ai_usage : null} /></Td>
                  <Td className="text-ink-2">{done ? pct(v.ai_confidence) : "—"}</Td>
                  <Td>{done ? <Severity value={e.risk_class} /> : <span className="text-ink-3">{titleCase(v.status)}</span>}</Td>
                  <Td><StrengthBar score={v.top_evidence_strength} level={v.evidence_strength_level} /></Td>
                  <Td className="text-[12px]">
                    {v.review_status === "PENDING_REVIEW"
                      ? <span className="text-sev-high">{v.human_review_required ? "Sign-off required" : "Pending"}</span>
                      : <span className="text-ink-2">{titleCase(v.review_status)}</span>}
                  </Td>
                  <Td className="whitespace-nowrap text-ink-2">{fmtDate(v.completed_at)}</Td>
                </tr>
              );
            })}
          </tbody>
        </Table>
        {data.vendors.length === 0 && (
          <div className="p-5"><Empty title="No assessment yet" action={<Button asChild><Link href="/import">Start an assessment</Link></Button>}>
            The workbook is imported but no assessment has been run.</Empty></div>
        )}
      </Panel>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <Panel title="Criticality"><Distribution data={data.criticality_distribution} order={TIER_ORDER} /></Panel>
        <Panel title="AI security risk"><Distribution data={data.risk_distribution} order={RISK_ORDER} /></Panel>
        <Panel title="Recent runs" bodyClass="p-0">
          <ul className="divide-y divide-rule-2">
            {data.recent_runs.map((r) => (
              <li key={r.id}>
                <Link href={`/runs/${r.id}`} className="block px-5 py-3 hover:bg-paper">
                  <div className="flex justify-between text-[13px]">
                    <span className="font-semibold">{r.parent_run_id ? "Reassessment" : "Full assessment"}</span>
                    <span className={r.status === "COMPLETED" ? "text-pine" : r.status === "FAILED" ? "text-sev-critical" : "text-sev-medium"}>{titleCase(r.status)}</span>
                  </div>
                  <div className="text-[12px] text-ink-3">{r.completed_vendors} of {r.total_vendors} vendors, {fmtDate(r.created_at, true)}</div>
                </Link>
              </li>
            ))}
          </ul>
        </Panel>
      </div>
    </>
  );
}
