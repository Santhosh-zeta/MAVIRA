// Severity, usage, method and strength indicators. Colour always paired with text.
import { cn, titleCase } from "@/lib/utils";

const SEV: Record<string, string> = {
  CRITICAL: "text-sev-critical bg-sev-critical-bg border-sev-critical",
  HIGH: "text-sev-high bg-sev-high-bg border-sev-high",
  MEDIUM: "text-sev-medium bg-sev-medium-bg border-sev-medium",
  LOW: "text-sev-low bg-sev-low-bg border-sev-low",
  NONE_IDENTIFIED: "text-sev-none bg-sev-none-bg border-sev-none",
};

export function Severity({ value, size = "sm" }: { value?: string | null; size?: "sm" | "lg" }) {
  if (!value) return <span className="text-ink-3">—</span>;
  return (
    <span className={cn("inline-flex items-center border-l-[3px] font-semibold", SEV[value] ?? SEV.NONE_IDENTIFIED,
      size === "lg" ? "px-2.5 py-1 text-[15px]" : "px-2 py-0.5 text-[12px]")}>
      {titleCase(value)}
    </span>
  );
}

const USAGE: Record<string, { label: string; cls: string }> = {
  YES: { label: "Yes", cls: "text-pine" },
  NO: { label: "No", cls: "text-ink-2" },
  INCONCLUSIVE: { label: "Inconclusive", cls: "text-ink-2" },
};

export function UsageMark({ value, size = "sm" }: { value?: string | null; size?: "sm" | "lg" }) {
  if (!value) return <span className="text-ink-3">—</span>;
  const u = USAGE[value];
  return (
    <span className={cn("inline-flex items-center gap-1.5 font-semibold", u.cls, size === "lg" ? "text-[15px]" : "text-[13px]")}>
      <span aria-hidden className={cn("inline-block rounded-full", size === "lg" ? "h-2.5 w-2.5" : "h-2 w-2",
        value === "YES" ? "bg-pine" : value === "NO" ? "bg-ink-3" : "border-2 border-ink-3 bg-transparent")} />
      {u.label}
    </span>
  );
}

export function MethodTag({ value }: { value?: string | null }) {
  const map: Record<string, { label: string; cls: string; title: string }> = {
    LIVE: { label: "Live", cls: "bg-pine-2 text-pine", title: "Fetched from the public web during this run" },
    CACHED: { label: "Cached snapshot", cls: "bg-highlight text-[#6b5a10]", title: "Verbatim text captured in an earlier analyst OSINT session; retrieval date shown" },
    DEMO_MOCK: { label: "Fictional fixture", cls: "bg-sev-critical-bg text-sev-critical", title: "Fictional test data — not real evidence" },
  };
  const m = value ? map[value] : undefined;
  if (!m) return null;
  return <span title={m.title} className={cn("inline-block rounded-[3px] px-1.5 py-px text-[11px] font-semibold", m.cls)}>{m.label}</span>;
}

export function StrengthBar({ score, level }: { score?: number | null; level?: string | null }) {
  if (score == null) return <span className="text-ink-3">—</span>;
  return (
    <span className="inline-flex items-center gap-2" title={`Evidence strength ${score}/100`}>
      <span className="relative h-1.5 w-14 overflow-hidden rounded bg-rule-2" aria-hidden>
        <span className="absolute inset-y-0 left-0 bg-ink-2" style={{ width: `${Math.min(100, score)}%` }} />
      </span>
      <span className="text-[12px] text-ink-2">{titleCase(level)} <span className="text-ink-3">{Math.round(score)}</span></span>
    </span>
  );
}

const NATURE: Record<string, string> = {
  SERVICE_INTEGRATED: "In contracted service",
  PRODUCT_FEATURE: "Product capability",
  INTERNAL_OPERATIONAL_USE: "Internal use",
  PARTNER_DEPENDENCY: "Third-party dependency",
  HIRING_SIGNAL: "Hiring signal",
  MARKETING_ONLY: "Marketing claim",
  INDUSTRY_COMMENTARY: "Commentary",
  UNKNOWN: "Unclear",
};
export function natureLabel(n?: string | null) { return n ? NATURE[n] ?? n : "—"; }

export function NatureTag({ value }: { value?: string | null }) {
  const strong = value === "SERVICE_INTEGRATED" || value === "PRODUCT_FEATURE";
  const muted = value === "INDUSTRY_COMMENTARY" || value === "MARKETING_ONLY";
  return (
    <span className={cn("inline-block rounded-[3px] border px-1.5 py-px text-[11px] font-semibold",
      strong ? "border-pine text-pine" : muted ? "border-rule text-ink-3" : "border-ink-3 text-ink-2")}>
      {natureLabel(value)}
    </span>
  );
}
