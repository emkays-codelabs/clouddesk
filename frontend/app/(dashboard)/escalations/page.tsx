"use client";

import Link from "next/link";
import { DataState } from "@/components/ui/DataState";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { api } from "@/lib/api";
import { canAct, useAuth } from "@/lib/auth";
import { formatDate } from "@/lib/format";
import { usePolling } from "@/lib/hooks";
import type { Escalation } from "@/lib/types";

const NEXT: Record<Escalation["status"], Escalation["status"] | null> = {
  open: "acknowledged",
  acknowledged: "resolved",
  resolved: null,
};

export default function EscalationsPage() {
  const { user } = useAuth();
  const { data, error, loading, refresh } = usePolling(() => api.escalations(), [], { intervalMs: 10000 });
  async function advance(e: Escalation) {
    const next = NEXT[e.status];
    if (!next) return;
    await api.updateEscalation(e.id, next);
    await refresh();
  }
  return (
    <div>
      <h1 className="mb-4 text-2xl font-semibold">Escalations</h1>
      <DataState loading={loading} error={error} hasData={!!data}>
        {data && data.length === 0 ? (
          <EmptyState title="No escalations" description="Policy cases and rejected approvals appear here." />
        ) : (
          <table className="w-full text-left text-sm">
            <thead className="text-slate-500">
              <tr>
                <th className="py-2">Ticket</th>
                <th>Team</th>
                <th>Reason</th>
                <th>Status</th>
                <th>Opened</th>
                <th />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {data?.map((e) => (
                <tr key={e.id}>
                  <td className="py-2">
                    <Link className="font-medium hover:underline" href={`/tickets/${e.ticket_id}`}>
                      {e.ticket_number}
                    </Link>
                  </td>
                  <td>{e.assigned_team}</td>
                  <td className="max-w-md truncate" title={e.reason}>
                    {e.reason}
                  </td>
                  <td>{e.status}</td>
                  <td>{formatDate(e.created_at)}</td>
                  <td>
                    {NEXT[e.status] ? (
                      <Button variant="secondary" disabled={!canAct(user)} onClick={() => void advance(e)}>
                        Mark {NEXT[e.status]}
                      </Button>
                    ) : null}
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
