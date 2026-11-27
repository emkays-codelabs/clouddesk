"use client";

import type { ReactNode } from "react";
import { NetworkError } from "@/lib/api";
import { Spinner } from "./Spinner";

/** Shows a spinner while loading and a clear message when a request failed; otherwise the children. */
export function DataState({
  loading,
  error,
  hasData,
  children,
}: {
  loading: boolean;
  error: Error | null;
  hasData: boolean;
  children: ReactNode;
}) {
  if (error instanceof NetworkError) {
    return (
      <div role="alert" className="mb-4 rounded border border-amber-300 bg-amber-50 p-3 text-sm">
        The server cannot be reached. The page will keep trying.
        {hasData ? <div className="mt-3">{children}</div> : null}
      </div>
    );
  }
  if (error) {
    return (
      <div role="alert" className="rounded border border-red-300 bg-red-50 p-3 text-sm text-red-800">
        {error.message}
      </div>
    );
  }
  if (loading && !hasData) return <Spinner />;
  return <>{children}</>;
}
