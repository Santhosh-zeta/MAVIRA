"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { FileUp, FileSearch, History, LayoutList, SlidersHorizontal } from "lucide-react";
import { useApi } from "@/lib/hooks";
import type { Health } from "@/lib/api";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/", label: "Vendor register", icon: LayoutList },
  { href: "/import", label: "Import workbook", icon: FileUp },
  { href: "/evidence", label: "Evidence", icon: FileSearch },
  { href: "/methodology", label: "Methodology", icon: SlidersHorizontal },
  { href: "/audit", label: "Audit trail", icon: History },
];

export function Shell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const { data: health, error } = useApi<Health>("/health");
  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      <aside className="flex shrink-0 flex-col bg-rail text-[#C9D3D1] md:sticky md:top-0 md:h-screen md:w-60">
        <div className="px-5 pb-4 pt-5">
          <Link href="/" className="block">
            <span className="block text-[19px] font-bold tracking-[0.02em] text-white">MAVIRA</span>
            <span className="block text-[12px] leading-snug text-[#93A3A0]">Meridian vendor AI risk assessment</span>
          </Link>
        </div>
        <nav aria-label="Main" className="flex gap-1 overflow-x-auto px-3 md:flex-col md:overflow-visible">
          {NAV.map(({ href, label, icon: Icon }) => {
            const active = href === "/" ? path === "/" || path.startsWith("/vendors") || path.startsWith("/runs") : path.startsWith(href);
            return (
              <Link key={href} href={href} aria-current={active ? "page" : undefined}
                className={cn("flex items-center gap-2.5 whitespace-nowrap rounded-[5px] px-3 py-2 text-[13px] font-medium",
                  active ? "bg-rail-2 text-white" : "hover:bg-rail-2/60 hover:text-white")}>
                <Icon size={15} aria-hidden /> {label}
              </Link>
            );
          })}
        </nav>
        <div className="mt-auto hidden border-t border-rail-2 px-5 py-4 text-[12px] leading-relaxed md:block">
          {error && <p className="text-[#E7A39B]">Backend not reachable</p>}
          {health && (
            <>
              <p className="font-semibold text-white">
                {health.osint_mode === "LIVE" ? `Live OSINT via ${health.search_provider}` : "Cached OSINT snapshot"}
              </p>
              <p className="text-[#93A3A0]">{health.llm_enabled ? health.analyzer : "Rule-based analyzer, no LLM"}</p>
              <p className="mt-2 text-[#93A3A0]">Confidential. Keep findings inside this exercise.</p>
            </>
          )}
        </div>
      </aside>
      <main className="min-w-0 flex-1 px-4 py-6 md:px-8 md:py-8">
        <div className="mx-auto max-w-[1280px]">{children}</div>
      </main>
    </div>
  );
}

export function PageHeader({ title, sub, actions }: { title: React.ReactNode; sub?: React.ReactNode; actions?: React.ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-[24px] font-bold leading-tight">{title}</h1>
        {sub && <div className="mt-1 max-w-[75ch] text-ink-2">{sub}</div>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}
