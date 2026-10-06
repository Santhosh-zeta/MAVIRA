"use client";
import { useState } from "react";
import { ExternalLink } from "lucide-react";
import { Dialog, DialogContent, DialogTrigger, Loading } from "@/components/ui/primitives";
import { MethodTag, NatureTag, StrengthBar } from "@/components/indicators";
import { api, type EvidenceItem, type SourceRef } from "@/lib/api";
import { fmtDate, pct, titleCase } from "@/lib/utils";

function SourceViewer({ sourceId, start, end }: { sourceId: string; start: number | null; end: number | null }) {
  const [src, setSrc] = useState<SourceRef | null>(null);
  const [err, setErr] = useState<string | null>(null);
  if (!src && !err) api.get<SourceRef>(`/sources/${sourceId}`).then(setSrc).catch((e) => setErr(e.message));
  if (err) return <p className="text-sev-critical">{err}</p>;
  if (!src) return <Loading label="Loading source" />;
  const text = src.content ?? "";
  const hasSpan = start != null && end != null && end > start;
  return (
    <div className="space-y-4">
      <SourceMeta s={src} />
      <div className="max-h-[52vh] overflow-y-auto whitespace-pre-wrap rounded border border-rule-2 bg-paper p-4 source-fact">
        {hasSpan ? (<>{text.slice(0, start!)}<mark id="hl">{text.slice(start!, end!)}</mark>{text.slice(end!)}</>) : text}
      </div>
      <p className="text-[12px] text-ink-3">
        Stored text used for validation. Content hash {src.content_hash?.slice(0, 16)}…
        {src.cache_origin && <> {src.cache_origin}.</>}
      </p>
    </div>
  );
}

export function SourceMeta({ s }: { s: SourceRef }) {
  return (
    <dl className="grid grid-cols-2 gap-x-6 gap-y-1.5 text-[12px] sm:grid-cols-4">
      <div className="col-span-2 sm:col-span-4">
        <dt className="sr-only">URL</dt>
        <dd><a href={s.url} target="_blank" rel="noopener noreferrer nofollow" className="inline-flex items-center gap-1 break-all font-semibold text-pine hover:underline">
          {s.title || s.url}<ExternalLink size={12} aria-hidden /></a>
          <div className="break-all text-ink-3">{s.url}</div></dd>
      </div>
      <div><dt className="text-ink-3">Source type</dt><dd>{titleCase(s.source_type)}</dd></div>
      <div><dt className="text-ink-3">Reliability</dt><dd>{titleCase(s.reliability_level)}</dd></div>
      <div><dt className="text-ink-3">Retrieved</dt><dd>{fmtDate(s.retrieved_at)}</dd></div>
      <div><dt className="text-ink-3">Collection</dt><dd><MethodTag value={s.collection_method} /></dd></div>
      {s.published_date && <div><dt className="text-ink-3">Published</dt><dd>{fmtDate(s.published_date)}</dd></div>}
    </dl>
  );
}

export function EvidenceCard({ e, showVendor }: { e: EvidenceItem; showVendor?: boolean }) {
  const rejected = e.validation_status !== "VALID";
  return (
    <article className="grid gap-0 overflow-hidden rounded-md border border-rule bg-surface lg:grid-cols-[3fr_2fr]">
      <div className="p-5">
        <div className="mb-2 flex flex-wrap items-center gap-2 text-[12px] text-ink-2">
          <span className="font-semibold text-ink">Source fact</span>
          {showVendor && <span>{e.vendor_ref} {e.vendor_name}</span>}
          <MethodTag value={e.source.collection_method} />
          {rejected && <span className="font-semibold text-sev-critical">Rejected: {e.rejection_reason}</span>}
        </div>
        <blockquote className={rejected ? "source-fact text-ink-3 line-through" : "source-fact"}>
          <mark className="hl">{e.exact_excerpt}</mark>
        </blockquote>
        <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-[12px] text-ink-2">
          <span className="break-all">{e.source.domain}</span>
          <span>{titleCase(e.source.source_type)}</span>
          <span>Retrieved {fmtDate(e.source.retrieved_at)}</span>
          <Dialog>
            <DialogTrigger className="font-semibold text-pine hover:underline">View in source</DialogTrigger>
            <DialogContent title="Source document" wide>
              <SourceViewer sourceId={e.source.id} start={e.excerpt_start} end={e.excerpt_end} />
            </DialogContent>
          </Dialog>
        </div>
      </div>
      <div className="border-t border-rule-2 bg-paper/60 p-5 lg:border-l lg:border-t-0">
        <div className="mb-2 flex flex-wrap items-center gap-2">
          <span className="text-[12px] font-semibold text-ink">System interpretation</span>
          <NatureTag value={e.nature} />
        </div>
        <p className="text-[13px] font-semibold">{e.claim}</p>
        <p className="mt-1.5 text-[12px] leading-relaxed text-ink-2">{e.interpretation}</p>
        <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1.5 text-[12px]">
          <div><dt className="text-ink-3">Evidence strength</dt><dd><StrengthBar score={e.strength_score} level={e.strength_level} /></dd></div>
          <div><dt className="text-ink-3">Classification confidence</dt><dd>{pct(e.confidence)}</dd></div>
          <div><dt className="text-ink-3">AI types</dt><dd>{e.ai_types.join(", ")}</dd></div>
          <div><dt className="text-ink-3">Service relevance</dt><dd>{pct(e.service_relevance)}</dd></div>
        </dl>
        {e.strength_breakdown && (
          <details className="mt-3 text-[12px]">
            <summary className="cursor-pointer text-ink-2 hover:text-ink">How strength was scored</summary>
            <table className="mt-2 w-full">
              <tbody>
                {Object.entries(e.strength_breakdown).map(([k, b]) => (
                  <tr key={k} className="border-b border-rule-2">
                    <td className="py-1">{titleCase(k)}</td>
                    <td className="py-1 text-right text-ink-2">{b.value.toFixed(2)} × {b.weight}</td>
                    <td className="py-1 text-right font-semibold">{b.points}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="mt-1 text-ink-3">Proposed by {e.proposed_by}; excerpt matched verbatim in the stored source.</p>
          </details>
        )}
      </div>
    </article>
  );
}
