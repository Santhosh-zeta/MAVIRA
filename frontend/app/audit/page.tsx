"use client";
import Link from "next/link";
import { PageHeader } from "@/components/shell";
import { ErrorNote, Loading, Panel, Table, Td, Th } from "@/components/ui/primitives";
import { useApi } from "@/lib/hooks";
import { fmtDate, titleCase } from "@/lib/utils";

interface Ev { id: string; event_type: string; actor: string; run_id: string | null; assessment_id: string | null; detail: Record<string, unknown>; created_at: string }

function summarize(d: Record<string, unknown>) {
  return Object.entries(d).filter(([, v]) => v !== null && v !== undefined && !(Array.isArray(v) && v.length > 6))
    .map(([k, v]) => `${k.replace(/_/g, " ")}: ${Array.isArray(v) ? v.join(", ") : typeof v === "object" ? JSON.stringify(v) : String(v)}`)
    .join("; ");
}

export default function AuditPage() {
  const { data, error, loading } = useApi<Ev[]>("/audit?limit=300", { pollMs: 10000 });
  return (
    <>
      <PageHeader title="Audit trail" sub="Append-only record of imports, runs, per-vendor results, reviews, methodology changes and exports." />
      {loading && <Loading />}
      {error && <ErrorNote>{error}</ErrorNote>}
      {data && (
        <Panel bodyClass="p-0">
          <Table>
            <thead><tr><Th className="w-44">Time</Th><Th className="w-44">Event</Th><Th className="w-32">Actor</Th><Th>Detail</Th><Th className="w-20">Link</Th></tr></thead>
            <tbody>{data.map((e) => (
              <tr key={e.id}>
                <Td className="whitespace-nowrap text-ink-2">{fmtDate(e.created_at, true)}</Td>
                <Td className="font-semibold">{titleCase(e.event_type)}</Td>
                <Td>{e.actor}</Td>
                <Td className="break-words text-[12px] text-ink-2">{summarize(e.detail)}</Td>
                <Td>{e.assessment_id ? <Link className="text-pine hover:underline" href={`/vendors/${e.assessment_id}`}>Vendor</Link>
                  : e.run_id ? <Link className="text-pine hover:underline" href={`/runs/${e.run_id}`}>Run</Link> : null}</Td>
              </tr>))}</tbody>
          </Table>
        </Panel>
      )}
    </>
  );
}
