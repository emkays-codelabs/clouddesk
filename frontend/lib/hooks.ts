"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export type Loaded<T> = {
  data: T | null;
  error: Error | null;
  loading: boolean;
  refresh: () => Promise<void>;
};

/**
 * Load once, and again whenever `deps` change or `refresh` is called.
 * With `intervalMs` it also polls (the ticket screen polls /workflow every 2 s while a run is going).
 * Polling stops when `stopWhen(data)` is true, and while the tab is hidden.
 */
export function usePolling<T>(
  load: () => Promise<T>,
  deps: unknown[],
  options: { intervalMs?: number; stopWhen?: (data: T) => boolean } = {},
): Loaded<T> {
  const { intervalMs, stopWhen } = options;
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [loading, setLoading] = useState(true);
  const loadRef = useRef(load);
  loadRef.current = load;
  const stopRef = useRef(stopWhen);
  stopRef.current = stopWhen;
  const alive = useRef(true);

  const refresh = useCallback(async () => {
    try {
      const next = await loadRef.current();
      if (!alive.current) return;
      setData(next);
      setError(null);
    } catch (e) {
      if (alive.current) setError(e instanceof Error ? e : new Error(String(e)));
    } finally {
      if (alive.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    alive.current = true;
    setLoading(true);
    void refresh();
    return () => {
      alive.current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    if (!intervalMs) return;
    const timer = setInterval(() => {
      if (typeof document !== "undefined" && document.hidden) return;
      if (data !== null && stopRef.current?.(data)) return;
      void refresh();
    }, intervalMs);
    return () => clearInterval(timer);
  }, [intervalMs, data, refresh]);

  return { data, error, loading, refresh };
}
