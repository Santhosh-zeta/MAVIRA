"use client";
import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle, CheckCircle2, FileSpreadsheet } from "lucide-react";
import { PageHeader } from "@/components/shell";
import { Button, ErrorNote, Panel, Table, Td, Th } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

interface Validation {
  valid: boolean; sheet_name: string; header_row: number; detected_columns: string[]; vendor_count: number;
  example_rows: string[]; missing_input_columns: string[]; missing_output_columns: string[];
  duplicate_vendor_ids: string[]; errors: string[]; warnings: string[];
  vendors: { row: number; vendor_ref: string; name: string; is_example: boolean; missing_fields: string[] }[];
}
interface UploadResult { import_id: string | null; accepted: boolean; validation: Validation }

export default function ImportPage() {
  const router = useRouter();
  const input = useRef<HTMLInputElement>(null);
  const [drag, setDrag] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [fileName, setFileName] = useState<string>("");

  async function handle(file?: File) {
    if (!file) return;
    setError(null); setResult(null); setBusy(true); setFileName(file.name);
    try {
      setResult(await api.upload<UploadResult>(file));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function start() {
    if (!result?.import_id) return;
    setBusy(true);
    try {
      const r = await api.post<{ run_id: string }>("/runs", { import_id: result.import_id });
      router.push(`/runs/${r.run_id}`);
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }

  const v = result?.validation;
  return (
    <>
      <PageHeader title="Import vendor inventory"
        sub="Upload Meridian's vendor workbook. Columns are matched by header name, the worked example row is kept untouched, and nothing is assessed until you start the run." />

      <div
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => { e.preventDefault(); setDrag(false); handle(e.dataTransfer.files[0]); }}
        className={cn("flex flex-col items-center justify-center gap-3 rounded-md border-2 border-dashed bg-surface px-6 py-12 text-center",
          drag ? "border-pine bg-pine-2" : "border-rule")}
      >
        <FileSpreadsheet size={28} className="text-ink-3" aria-hidden />
        <p className="text-[15px] font-semibold">Drop the .xlsx workbook here</p>
        <p className="text-ink-2">or</p>
        <Button variant="secondary" onClick={() => input.current?.click()} disabled={busy}>Choose a file</Button>
        <input ref={input} type="file" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" className="sr-only"
          onChange={(e) => handle(e.target.files?.[0])} aria-label="Workbook file" />
        <p className="text-[12px] text-ink-3">Excel workbook up to 10 MB. Processed locally; the file is not sent to any third party.</p>
      </div>

      {busy && !result && <p className="mt-4 text-ink-2" aria-live="polite">Validating {fileName}…</p>}
      {error && <div className="mt-4"><ErrorNote>{error}</ErrorNote></div>}

      {v && (
        <div className="mt-6 space-y-6">
          <Panel
            title={v.valid ? "Workbook is valid" : "Workbook cannot be imported"}
            aside={v.valid && (
              <Button onClick={start} disabled={busy}>{busy ? "Starting…" : `Start assessment of ${v.vendor_count} vendors`}</Button>
            )}
          >
            <div className="flex items-start gap-3">
              {v.valid ? <CheckCircle2 className="mt-0.5 text-pine" size={18} aria-hidden /> : <AlertTriangle className="mt-0.5 text-sev-critical" size={18} aria-hidden />}
              <dl className="grid flex-1 grid-cols-2 gap-x-8 gap-y-2 text-[13px] sm:grid-cols-4">
                <div><dt className="text-ink-3">Sheet</dt><dd className="font-semibold">{v.sheet_name}</dd></div>
                <div><dt className="text-ink-3">Header row</dt><dd className="font-semibold">{v.header_row}</dd></div>
                <div><dt className="text-ink-3">Vendors to assess</dt><dd className="font-semibold">{v.vendor_count}</dd></div>
                <div><dt className="text-ink-3">Worked example kept as-is</dt><dd className="font-semibold">{v.example_rows.join(", ") || "None"}</dd></div>
              </dl>
            </div>
            {v.errors.length > 0 && (
              <ul className="mt-4 list-disc space-y-1 pl-5 text-sev-critical">{v.errors.map((e) => <li key={e}>{e}</li>)}</ul>
            )}
            {v.warnings.length > 0 && (
              <div className="mt-4">
                <h3 className="mb-1 text-[13px] font-semibold">Warnings</h3>
                <ul className="list-disc space-y-1 pl-5 text-sev-medium">{v.warnings.map((w) => <li key={w}>{w}</li>)}</ul>
              </div>
            )}
            {v.duplicate_vendor_ids.length > 0 && <p className="mt-3 text-sev-critical">Duplicate vendor IDs: {v.duplicate_vendor_ids.join(", ")}</p>}
          </Panel>

          <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
            <Panel title="Vendors found" bodyClass="p-0">
              <Table>
                <thead><tr><Th>Row</Th><Th>ID</Th><Th>Vendor</Th><Th>Status</Th></tr></thead>
                <tbody>
                  {v.vendors.map((r) => (
                    <tr key={r.row}>
                      <Td className="text-ink-3">{r.row}</Td>
                      <Td className="font-semibold">{r.vendor_ref}</Td>
                      <Td>{r.name}</Td>
                      <Td className="text-[12px]">
                        {r.is_example ? <span className="text-ink-3">Worked example, not assessed</span>
                          : r.missing_fields.length ? <span className="text-sev-medium">Missing: {r.missing_fields.join(", ")}</span>
                          : <span className="text-pine">Ready</span>}
                      </Td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            </Panel>
            <Panel title="Columns detected">
              <ul className="space-y-1 text-[13px]">
                {v.detected_columns.map((c) => <li key={c}>{c}</li>)}
              </ul>
              {(v.missing_input_columns.length > 0 || v.missing_output_columns.length > 0) && (
                <p className="mt-3 text-[12px] text-sev-medium">
                  Not found: {[...v.missing_input_columns, ...v.missing_output_columns].join(", ")}
                </p>
              )}
            </Panel>
          </div>
        </div>
      )}
    </>
  );
}
