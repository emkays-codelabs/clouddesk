"use client";

import Link from "next/link";
import { use } from "react";
import { DataState } from "@/components/ui/DataState";
import { Card } from "@/components/ui/Card";
import { StatusPill } from "@/components/ui/StatusPill";
import { api } from "@/lib/api";
import { usePolling } from "@/lib/hooks";

export default function CustomerPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data, error, loading } = usePolling(() => api.customer(id), [id]);
  return (
    <div>
      <Link href="/customers" className="text-sm text-slate-600 hover:underline">
        ← Customers
      </Link>
      <DataState loading={loading} error={error} hasData={!!data}>
        {data ? (
          <div className="mt-2 space-y-4">
            <h1 className="text-2xl font-semibold">{data.name}</h1>
            <p className="text-sm text-slate-600">
              {data.company} · {data.email} · {data.plan_name} · {data.status}
            </p>
            <div className="grid gap-4 md:grid-cols-2">
              <Card title="Subscription">
                {data.subscription ? (
                  <p className="text-sm">
                    {data.subscription.plan}: {data.subscription.seats} seats, {data.subscription.status}, storage{" "}
                    {data.subscription.storage_used_gb}/{data.subscription.storage_quota_gb} GB
                  </p>
                ) : (
                  <p className="text-sm text-slate-500">No subscription.</p>
                )}
              </Card>
              <Card title="Workspace">
                {data.workspace ? (
                  <p className="text-sm">
                    {data.workspace.name}: {data.workspace.member_count} members,{" "}
                    {data.workspace.sso_enabled ? "SSO on" : "SSO off"}
                  </p>
                ) : (
                  <p className="text-sm text-slate-500">No workspace.</p>
                )}
              </Card>
            </div>
            <Card title="Tickets">
              <ul className="divide-y divide-slate-100 text-sm">
                {data.tickets.map((t) => (
                  <li key={t.id} className="flex justify-between py-2">
                    <Link className="hover:underline" href={`/tickets/${t.id}`}>
                      {t.ticket_number} · {t.subject}
                    </Link>
                    <StatusPill status={t.status} />
                  </li>
                ))}
              </ul>
            </Card>
            <Card title="What we remember">
              {data.memory.length === 0 ? (
                <p className="text-sm text-slate-500">Nothing yet.</p>
              ) : (
                <ul className="list-disc pl-5 text-sm">
                  {data.memory.map((m) => (
                    <li key={m.id}>{m.content}</li>
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
