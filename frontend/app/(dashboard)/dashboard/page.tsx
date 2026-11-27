"use client";

import Link from "next/link";
import { DataState } from "@/components/ui/DataState";
import { Card } from "@/components/ui/Card";
import { KPIStatCards } from "@/components/ui/KPIStatCards";
import { EmptyState } from "@/components/ui/EmptyState";
import { StatusPill } from "@/components/ui/StatusPill";
import { api } from "@/lib/api";
import { formatDate, humanize } from "@/lib/format";
import { usePolling } from "@/lib/hooks";

export default function DashboardPage() {
  const { data, error, loading } = usePolling(() => api.dashboard(), [], { intervalMs: 10000 });
  return (
    <div>
      <h1 className="mb-4 text-2xl font-semibold">Dashboard</h1>
      <DataState loading={loading} error={error} hasData={!!data}>
        {data ? (
          <div className="space-y-6">
            <KPIStatCards
              items={[
                { label: "Open tickets", value: data.open_tickets },
                { label: "Resolved today", value: data.resolved_today },
                { label: "Pending approvals", value: data.pending_approvals },
                { label: "Open escalations", value: data.escalations_open },
              ]}
            />
            <div className="grid gap-4 md:grid-cols-2">
              <Card title="By severity">
                <ul className="text-sm">
                  {Object.entries(data.by_severity).map(([k, v]) => (
                    <li key={k} className="flex justify-between py-0.5">
                      <span>{k}</span>
                      <span>{v}</span>
                    </li>
                  ))}
                </ul>
              </Card>
              <Card title="By category">
                <ul className="text-sm">
                  {Object.entries(data.by_category).map(([k, v]) => (
                    <li key={k} className="flex justify-between py-0.5">
                      <span>{humanize(k)}</span>
                      <span>{v}</span>
                    </li>
                  ))}
                </ul>
              </Card>
            </div>
            <Card title="Recent tickets">
              {data.recent_tickets.length === 0 ? (
                <EmptyState title="No tickets yet" />
              ) : (
                <ul className="divide-y divide-slate-100 text-sm">
                  {data.recent_tickets.map((t) => (
                    <li key={t.id} className="flex items-center justify-between py-2">
                      <Link className="font-medium hover:underline" href={`/tickets/${t.id}`}>
                        {t.ticket_number} · {t.subject}
                      </Link>
                      <span className="flex items-center gap-3">
                        <StatusPill status={t.status} />
                        <span className="text-slate-500">{formatDate(t.updated_at)}</span>
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          </div>
        ) : null}
      </DataState>
    </div>
  );
}
