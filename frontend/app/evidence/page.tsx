"use client";
import { useMemo, useState } from "react";
import { PageHeader } from "@/components/shell";
import { Empty, ErrorNote, Input, Loading, Select } from "@/components/ui/primitives";
import { natureLabel } from "@/components/indicators";
import { EvidenceCard } from "@/components/evidence";
import { useApi } from "@/lib/hooks";
import type { EvidenceItem } from "@/lib/api";

const NATURES = ["SERVICE_INTEGRATED", "PRODUCT_FEATURE", "PARTNER_DEPENDENCY", "INTERNAL_OPERATIONAL_USE",
  "HIRING_SIGNAL", "MARKETING_ONLY", "INDUSTRY_COMMENTARY"];

export default function EvidencePage() {
  const [status, setStatus] = useState("VALID");
  const { data, error, loading } = useApi<EvidenceItem[]>(`/evidence?status=${status}`);
  const [vendor, setVendor] = useState("");
  const [nature, setNature] = useState("signals");
  const [q, setQ] = useState("");

  const vendors = useMemo(() => [...new Map((data ?? []).map((e) => [e.vendor_ref, e.vendor_name])).entries()], [data]);
  const list = (data ?? []).filter((e) =>
    (!vendor || e.vendor_ref === vendor) &&
    (nature === "all" || (nature === "signals" ? e.nature !== "INDUSTRY_COMMENTARY" : e.nature === nature)) &&
    (!q || `${e.exact_excerpt} ${e.claim} ${e.source.url}`.toLowerCase().includes(q.toLowerCase())));

  return (
    <>
      <PageHeader title="Evidence"
        sub="Verbatim excerpts from public sources, set beside the system's interpretation of them. Excerpts that could not be matched exactly in their source are rejected and never used." />
      <div className="mb-5 flex flex-wrap items-end gap-3">
        <label className="text-[13px]"><span className="mb-1 block font-semibold">Vendor</span>
          <Select value={vendor} onChange={(e) => setVendor(e.target.value)}>
            <option value="">All vendors</option>
            {vendors.map(([ref, name]) => <option key={ref ?? ""} value={ref ?? ""}>{ref} {name}</option>)}
          </Select></label>
        <label className="text-[13px]"><span className="mb-1 block font-semibold">Signal type</span>
          <Select value={nature} onChange={(e) => setNature(e.target.value)}>
            <option value="signals">AI signals (excludes commentary)</option>
            <option value="all">Everything</option>
            {NATURES.map((n) => <option key={n} value={n}>{natureLabel(n)}</option>)}
          </Select></label>
        <label className="text-[13px]"><span className="mb-1 block font-semibold">Validation</span>
          <Select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="VALID">Validated</option>
            <option value="REJECTED">Rejected</option>
            <option value="ALL">All</option>
          </Select></label>
        <label className="min-w-[220px] flex-1 text-[13px]"><span className="mb-1 block font-semibold">Search text</span>
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Words in excerpt, claim or URL" /></label>
      </div>
      {loading && <Loading />}
      {error && <ErrorNote>{error}</ErrorNote>}
      {data && <p className="mb-3 text-[13px] text-ink-2">{list.length} of {data.length} excerpts</p>}
      <div className="space-y-4">
        {list.map((e) => <EvidenceCard key={e.id} e={e} showVendor />)}
      </div>
      {data && list.length === 0 && <Empty title="No excerpts match these filters">Change the filters, or run an assessment first.</Empty>}
    </>
  );
}
