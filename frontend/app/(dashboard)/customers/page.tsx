"use client";

import Link from "next/link";
import { useState } from "react";
import { DataState } from "@/components/ui/DataState";
import { EmptyState } from "@/components/ui/EmptyState";
import { api } from "@/lib/api";
import { usePolling } from "@/lib/hooks";

export default function CustomersPage() {
  const [search, setSearch] = useState("");
  const { data, error, loading } = usePolling(() => api.customers({ search, page_size: 50 }), [search]);
  return (
    <div>
      <h1 className="mb-4 text-2xl font-semibold">Customers</h1>
      <input
        aria-label="Search customers"
        placeholder="Search name or company"
        className="mb-4 rounded border border-slate-300 px-3 py-2 text-sm"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />
      <DataState loading={loading} error={error} hasData={!!data}>
        {data && data.items.length === 0 ? (
          <EmptyState title="No customers match" />
        ) : (
          <table className="w-full text-left text-sm">
            <thead className="text-slate-500">
              <tr>
                <th className="py-2">Name</th>
                <th>Company</th>
                <th>Plan</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {data?.items.map((c) => (
                <tr key={c.id}>
                  <td className="py-2">
                    <Link className="font-medium hover:underline" href={`/customers/${c.id}`}>
                      {c.name}
                    </Link>
                  </td>
                  <td>{c.company}</td>
                  <td>{c.plan_name}</td>
                  <td>{c.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </DataState>
    </div>
  );
}
