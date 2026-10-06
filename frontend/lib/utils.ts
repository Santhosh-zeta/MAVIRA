import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function fmtDate(iso?: string | null, withTime = false) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("en-GB", withTime
    ? { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }
    : { day: "2-digit", month: "short", year: "numeric" });
}

export function titleCase(v?: string | null) {
  if (!v) return "—";
  if (v === "NONE_IDENTIFIED") return "None identified";
  return v.replace(/_/g, " ").toLowerCase().replace(/^\w/, (c) => c.toUpperCase());
}

export function pct(v?: number | null) {
  return v == null ? "—" : `${Math.round(v * 100)}%`;
}
