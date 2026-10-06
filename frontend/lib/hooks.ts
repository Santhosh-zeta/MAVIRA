"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api";

export function useApi<T>(path: string | null, opts: { pollMs?: number; stopWhen?: (d: T) => boolean } = {}) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const stopRef = useRef(opts.stopWhen);
  stopRef.current = opts.stopWhen;

  const load = useCallback(async () => {
    if (!path) return;
    try {
      const d = await api.get<T>(path);
      setData(d);
      setError(null);
      return d;
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [path]);

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | undefined;
    let alive = true;
    const tick = async () => {
      const d = await load();
      if (!alive || !opts.pollMs) return;
      if (d && stopRef.current?.(d)) return;
      timer = setTimeout(tick, opts.pollMs);
    };
    tick();
    return () => { alive = false; if (timer) clearTimeout(timer); };
  }, [load, opts.pollMs]);

  return { data, error, loading, reload: load };
}
