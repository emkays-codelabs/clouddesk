"use client";

import { DataState } from "@/components/ui/DataState";
import { Card } from "@/components/ui/Card";
import { KPIStatCards } from "@/components/ui/KPIStatCards";
import { api } from "@/lib/api";
import { describeCost } from "@/lib/format";
import { usePolling } from "@/lib/hooks";

export default function AgentsPage() {
  const { data, error, loading } = usePolling(() => api.agents(), [], { intervalMs: 10000 });
  const cost = describeCost(data?.stats.total_estimated_cost_usd ?? 0, data?.stats.cost_basis);
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Agents</h1>
      <DataState loading={loading} error={error} hasData={!!data}>
        {data ? (
          <>
            <KPIStatCards
              items={[
                { label: "Runs", value: data.stats.runs_total },
                { label: "Failed", value: data.stats.runs_failed },
                { label: "Tokens", value: data.stats.total_tokens.toLocaleString("en-IN") },
              ]}
            />
            <Card title={cost.label}>
              <span className="text-lg font-semibold">{cost.text}</span>
              <p className="mt-1 text-xs text-slate-500">
                Model cost only; refund amounts are separate and shown in INR.
              </p>
            </Card>
            <Card title="The six agents">
              <ul className="divide-y divide-slate-100 text-sm">
                {data.agents.map((a) => (
                  <li key={a.name} className="py-2">
                    <span className="font-medium">{a.name}</span>{" "}
                    <span className="text-slate-500">({a.role}, {a.runs} runs)</span>
                    <div className="text-slate-600">{a.description}</div>
                    {a.tools.length ? <div className="text-xs text-slate-500">tools: {a.tools.join(", ")}</div> : null}
                  </li>
                ))}
              </ul>
            </Card>
            <Card title="The graph">
              <ol className="list-decimal pl-5 text-sm">
                {data.graph.nodes.map((n) => (
                  <li key={n.id}>{n.label}</li>
                ))}
              </ol>
            </Card>
          </>
        ) : null}
      </DataState>
    </div>
  );
}
