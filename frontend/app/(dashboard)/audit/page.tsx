"use client";

import { useState } from "react";
import { DataState } from "@/components/ui/DataState";
import { EmptyState } from "@/components/ui/EmptyState";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { usePolling } from "@/lib/hooks";

export default function AuditPage() {
  const [actor, setActor] = useState("");
  const { data, error, loading } = usePolling(() => api.audit({ actor, page_size: 50 }), [actor]);
  return (
    <div>
      <h1 className="mb-4 text-2xl font-semibold">Audit log</h1>
      <input
        aria-label="Filter by actor"
        placeholder="Filter by actor"
        className="mb-4 rounded border border-slate-300 px-3 py-2 text-sm"
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
                  <td className="py-2">{formatDate(a.created_at)}</td>
                  <td>{a.actor}</td>
                  <td>{a.action}</td>
                  <td className="font-mono text-xs">{a.request_id ?? "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </DataState>
    </div>
  );
}
