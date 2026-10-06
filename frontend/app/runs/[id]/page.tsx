"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Check, Circle, Loader2, XCircle } from "lucide-react";
import { PageHeader } from "@/components/shell";
import { Button, ErrorNote, Loading, Panel } from "@/components/ui/primitives";
import { Severity, UsageMark } from "@/components/indicators";
import { useApi } from "@/lib/hooks";
import type { RunDetail } from "@/lib/api";
import { cn, fmtDate, titleCase } from "@/lib/utils";

const FINAL = ["COMPLETED", "PARTIAL", "FAILED"];

export default function RunPage() {
  const { id } = useParams<{ id: string }>();
  const { data, error, loading } = useApi<RunDetail>(`/runs/${id}`, { pollMs: 800, stopWhen: (d) => FINAL.includes(d.status) });
  if (loading) return <Loading />;
  if (error || !data) return <ErrorNote>{error ?? "Run not found"}</ErrorNote>;
  const done = FINAL.includes(data.status);
  const errs = data.assessments.flatMap((a) => (a.errors ?? []).map((e) => ({ vendor: a.vendor_ref, ...e })));

  return (
    <>
      <PageHeader
        title={done ? `Assessment ${titleCase(data.status).toLowerCase()}` : "Assessment running"}
        sub={<>Started {fmtDate(data.created_at, true)} by {data.triggered_by}. Methodology {data.methodology_version}, {data.osint_mode === "LIVE" ? `live OSINT via ${data.search_provider}` : "cached OSINT snapshot"}, analyzer {data.analyzer}.</>}
        actions={done && <Button asChild><Link href="/">Open vendor register</Link></Button>}
      />

      <div className="mb-6">
        <div className="mb-1.5 flex justify-between text-[13px]">
          <span className="font-semibold">{data.completed_vendors + data.failed_vendors} of {data.total_vendors} vendors processed</span>
          <span className="text-ink-2">{Math.round(data.progress * 100)}%</span>
        </div>
        <div className="h-2 overflow-hidden rounded bg-rule-2" role="progressbar" aria-valuenow={Math.round(data.progress * 100)} aria-valuemin={0} aria-valuemax={100}>
          <div className="h-full bg-pine transition-[width] duration-500" style={{ width: `${data.progress * 100}%` }} />
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {data.assessments.map((a) => {
          const active = a.status === "RUNNING";
          const finished = a.status === "COMPLETED" || a.status === "PARTIAL";
          return (
            <Panel key={a.id}
              title={<span>{a.vendor_ref} <span className="font-normal text-ink-2">{a.vendor_name}</span></span>}
              aside={a.status === "FAILED" ? <span className="text-sev-critical">Failed</span> : finished ? <span className="text-pine">Done</span> : active ? "Running" : "Queued"}>
              <ol className="space-y-1.5 text-[13px]">
                {a.stages.map((s, i) => {
                  const current = active && !s.done && (i === 0 || a.stages[i - 1].done);
                  return (
                    <li key={s.key} className={cn("flex items-center gap-2", s.done ? "text-ink" : "text-ink-3")}>
                      {s.done ? <Check size={14} className="text-pine" aria-hidden />
                        : current ? <Loader2 size={14} className="animate-spin text-ink-2" aria-hidden />
                        : a.status === "FAILED" ? <XCircle size={14} className="text-sev-critical" aria-hidden />
                        : <Circle size={14} aria-hidden />}
                      {s.label}
                    </li>
                  );
                })}
              </ol>
              {finished && (
                <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-rule-2 pt-3 text-[13px]">
                  <span>Criticality <Severity value={a.criticality_tier} /></span>
                  <span>AI <UsageMark value={a.ai_usage} /></span>
                  <span>Risk <Severity value={a.risk_class} /></span>
                  <Link href={`/vendors/${a.id}`} className="ml-auto font-semibold text-pine hover:underline">Open</Link>
                </div>
              )}
            </Panel>
          );
        })}
      </div>

      {errs.length > 0 && (
        <Panel title="Errors and warnings" className="mt-6" aside="One failed source never stops a vendor; one failed vendor never stops the run.">
          <ul className="space-y-1.5 text-[13px]">
            {errs.map((e, i) => <li key={i}><span className="font-semibold">{e.vendor}</span> <span className="text-ink-3">({e.stage})</span> {e.error}</li>)}
          </ul>
        </Panel>
      )}
    </>
  );
}
