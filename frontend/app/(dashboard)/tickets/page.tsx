"use client";

import Link from "next/link";
import { useState } from "react";
import { DataState } from "@/components/ui/DataState";
import { EmptyState } from "@/components/ui/EmptyState";
import { StatusPill } from "@/components/ui/StatusPill";
import { api } from "@/lib/api";
import { formatDate, humanize } from "@/lib/format";
import { usePolling } from "@/lib/hooks";

const STATUSES = ["", "new", "in_progress", "waiting_on_customer", "waiting_on_approval", "escalated", "resolved", "closed"];
const SEVERITIES = ["", "low", "medium", "high", "critical"];

export default function TicketsPage() {
  const [status, setStatus] = useState("");
  const [severity, setSeverity] = useState("");
  const [search, setSearch] = useState("");
  const { data, error, loading } = usePolling(
    () => api.tickets({ status, severity, search, page_size: 50 }),
    [status, severity, search],
    { intervalMs: 10000 },
  );
  return (
    <div>
      <h1 className="mb-4 text-2xl font-semibold">Tickets</h1>
      <div className="mb-4 flex flex-wrap gap-3 text-sm">
        <input
          aria-label="Search tickets"
          placeholder="Search subject or number"
          className="rounded border border-slate-300 px-3 py-2"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select aria-label="Status" className="rounded border border-slate-300 px-2" value={status} onChange={(e) => setStatus(e.target.value)}>
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s ? humanize(s) : "Any status"}
            </option>
          ))}
        </select>
        <select aria-label="Severity" className="rounded border border-slate-300 px-2" value={severity} onChange={(e) => setSeverity(e.target.value)}>
          {SEVERITIES.map((s) => (
            <option key={s} value={s}>
              {s || "Any severity"}
            </option>
          ))}
        </select>
      </div>
      <DataState loading={loading} error={error} hasData={!!data}>
        {data && data.items.length === 0 ? (
          <EmptyState title="No tickets match" description="Change the filters." />
        ) : (
          <table className="w-full text-left text-sm">
            <thead className="text-slate-500">
              <tr>
                <th className="py-2">Ticket</th>
                <th>Customer</th>
                <th>Status</th>
                <th>Severity</th>
                <th>Updated</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {data?.items.map((t) => (
                <tr key={t.id}>
                  <td className="py-2">
                    <Link className="font-medium hover:underline" href={`/tickets/${t.id}`}>
                      {t.ticket_number}
                    </Link>{" "}
                    {t.subject}
                  </td>
                  <td>{t.customer_name}</td>
                  <td>
                    <StatusPill status={t.status} />
                  </td>
                  <td>{t.severity ?? "-"}</td>
                  <td>{formatDate(t.updated_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </DataState>
    </div>
  );
}
