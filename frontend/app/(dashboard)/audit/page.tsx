"use client";

import { useState } from "react";
import { DataState } from "@/components/ui/DataState";
import { EmptyState } from "@/components/ui/EmptyState";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { usePolling } from "@/lib/hooks";

/** "POST /api/v1/tickets/x/run" as a small method badge plus the path. */
function ActionText({ action }: { action: string }) {
  const [method, ...rest] = action.split(" ");
  if (rest.length === 0) return <>{action}</>;
  return (
    <span className="flex items-center gap-2">
      <span className="rounded-md bg-brand-50 px-1.5 py-0.5 text-[10px] font-bold tracking-wide text-brand-700">
        {method}
      </span>
      <span className="break-all">{rest.join(" ")}</span>
    </span>
  );
}

export default function AuditPage() {
  const [actor, setActor] = useState("");
  const { data, error, loading } = usePolling(() => api.audit({ actor, page_size: 50 }), [actor]);
  return (
    <div>
      <h1 className="mb-4 text-2xl font-semibold">Audit log</h1>
      <input
        aria-label="Filter by actor"
        placeholder="Filter by actor"
        className="mb-4 w-64 rounded-xl border border-sand-200 bg-white px-3 py-2 text-sm"
        value={actor}
        onChange={(e) => setActor(e.target.value)}
      />
      <DataState loading={loading} error={error} hasData={!!data}>
        {data && data.items.length === 0 ? (
          <EmptyState title="No audit entries" description="Every change you make is recorded here." />
        ) : (
          <table className="w-full text-left text-sm">
            <thead className="text-slate-500">
              <tr>
                <th className="py-2">When</th>
                <th>Actor</th>
                <th>Action</th>
                <th>Request</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {data?.items.map((a) => (
                <tr key={a.id}>
                  <td className="whitespace-nowrap py-2 text-slate-600">{formatDate(a.created_at)}</td>
                  <td className="whitespace-nowrap">{a.actor}</td>
                  <td>
                    <ActionText action={a.action} />
                  </td>
                  <td className="whitespace-nowrap font-mono text-xs text-slate-500" title={a.request_id ?? undefined}>
                    {a.request_id ? a.request_id.slice(0, 8) : "-"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </DataState>
    </div>
  );
}
